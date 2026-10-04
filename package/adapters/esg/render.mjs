// Render only the adapter's local, escaped HTML. No network data or review claims.
import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const args = {};
for (let i = 2; i < process.argv.length; i += 2) {
  const key = process.argv[i];
  if (!['--out', '--chromium', '--playwright-module'].includes(key) || !process.argv[i + 1]) {
    throw new Error(`Unknown/incomplete argument: ${key}`);
  }
  args[key] = process.argv[i + 1];
}
if (!args['--out']) throw new Error('--out required');
const out = path.resolve(args['--out']);
let browser;
try {
  const candidates = [args['--playwright-module'] || process.env.ESG_PLAYWRIGHT_MODULE,
    'playwright',
    ...(process.env.NODE_PATH || '').split(path.delimiter).filter(Boolean).map(p => path.join(p, 'playwright')),
    path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')].filter(Boolean);
  let playwright, resolved;
  for (const candidate of candidates) {
    try { resolved = require.resolve(candidate); playwright = require(resolved); break; }
    catch (error) {
      if (candidate === args['--playwright-module'] || candidate === process.env.ESG_PLAYWRIGHT_MODULE) throw error;
    }
  }
  if (!playwright) throw new Error('Playwright missing. In adapters/esg run npm ci, then npx playwright install chromium; or set ESG_PLAYWRIGHT_MODULE.');
  const chromiumPath = args['--chromium'] || process.env.ESG_CHROMIUM_EXECUTABLE;
  browser = await playwright.chromium.launch({ headless: true, ...(chromiumPath ? { executablePath: chromiumPath } : {}) });
  const context = await browser.newContext({ viewport: { width: 794, height: 1123 }, deviceScaleFactor: 1, locale: 'ko-KR', timezoneId: 'UTC', javaScriptEnabled: false });
  const page = await context.newPage();
  await page.route('**/*', route => /^(file|data):/.test(route.request().url()) ? route.continue() : route.abort());
  await page.emulateMedia({ media: 'print', reducedMotion: 'reduce' });
  await page.goto(pathToFileURL(path.join(out, 'report.html')).href, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  const embeddedFont = await page.evaluate(async () => {
    const faces = await document.fonts.load('10pt "ESG NanumGothic"');
    return faces.length > 0 && faces.every(face => face.status === 'loaded');
  });
  if (!embeddedFont) throw new Error('Vendored Korean font did not load');
  const geometry = await page.evaluate(() => {
    const overflows = [];
    const rect = element => {
      const r = element.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height, right: r.right, bottom: r.bottom };
    };
    const tolerance = 1;
    const pages = [...document.querySelectorAll('.report-page')].map((sheet, i) => {
      const content = sheet.querySelector('.page-body');
      const footer = sheet.querySelector('.footer');
      const bounds = rect(sheet), bodyBounds = rect(content), footerBounds = rect(footer);
      for (const svg of sheet.querySelectorAll('svg')) {
        const view = svg.viewBox.baseVal;
        for (const text of svg.querySelectorAll('text')) {
          const box = text.getBBox();
          if (box.x < view.x - tolerance || box.y < view.y - tolerance ||
              box.x + box.width > view.x + view.width + tolerance ||
              box.y + box.height > view.y + view.height + tolerance) {
            overflows.push({ page: i + 1, id: sheet.id, element: 'SVG text', reason: 'glyph outside SVG viewBox', text: text.textContent });
          }
        }
      }
      for (const root of [sheet.querySelector('header'), content, footer]) {
        const limit = rect(root);
        if (root.scrollWidth > root.clientWidth + tolerance || root.scrollHeight > root.clientHeight + tolerance) {
          overflows.push({ page: i + 1, id: sheet.id, element: root.className || root.tagName, reason: 'scroll overflow' });
        }
        for (const element of root.querySelectorAll('*')) {
          const r = rect(element);
          if (r.width && r.height && (r.x < limit.x - tolerance || r.right > limit.right + tolerance || r.y < limit.y - tolerance || r.bottom > limit.bottom + tolerance)) {
            overflows.push({ page: i + 1, id: sheet.id, element: element.tagName, reason: 'element outside content geometry', bounds: r });
          }
        }
        const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
        let node;
        while ((node = walker.nextNode())) {
          if (!node.textContent.trim() || node.parentElement.closest('svg')) continue;
          const range = document.createRange();
          range.selectNodeContents(node);
          for (const r of range.getClientRects()) {
            if (r.left < limit.x - tolerance || r.right > limit.right + tolerance || r.bottom > limit.bottom + tolerance) {
              overflows.push({ page: i + 1, id: sheet.id, element: node.parentElement.tagName, reason: 'text outside content geometry' });
              break;
            }
          }
        }
      }
      if (bodyBounds.bottom > footerBounds.y + tolerance || footerBounds.bottom > bounds.bottom + tolerance) {
        overflows.push({ page: i + 1, id: sheet.id, reason: 'body/footer overlap or footer outside sheet' });
      }
      return { page: i + 1, id: sheet.id, sheet: bounds, content: bodyBounds, footer: footerBounds };
    });
    return { page_count: pages.length, paper: 'A4', screenshot_kind: 'HTML print sheets (PDF physical page count verified by Python)', pages, overflows };
  });
  await fs.writeFile(path.join(out, 'geometry.json'), JSON.stringify(geometry, null, 2) + '\n');
  await fs.mkdir(path.join(out, 'screenshots'), { recursive: true });
  const sheets = page.locator('.report-page');
  for (let i = 0; i < geometry.page_count; i++) {
    await sheets.nth(i).screenshot({ path: path.join(out, 'screenshots', `page-${String(i + 1).padStart(2, '0')}.png`), animations: 'disabled' });
  }
  if (geometry.overflows.length) throw new Error(`Geometry overflow: ${geometry.overflows.length} finding(s); inspect geometry.json and screenshots.`);
  await page.pdf({ path: path.join(out, 'report.pdf'), format: 'A4', preferCSSPageSize: true, printBackground: true, displayHeaderFooter: false, tagged: true, margin: { top: 0, bottom: 0, left: 0, right: 0 } });
  const packagePath = require.resolve('playwright/package.json', { paths: [path.dirname(resolved)] });
  const packageInfo = JSON.parse(await fs.readFile(packagePath, 'utf8'));
  await fs.writeFile(path.join(out, 'render.json'), JSON.stringify({ renderer: 'Playwright Node', playwright_version: packageInfo.version, browser_version: browser.version(), node_version: process.version, chromium_executable: chromiumPath || 'Playwright managed Chromium', screenshot_pages: geometry.page_count, network: 'blocked', independent_review: 'not_performed' }, null, 2) + '\n');
  console.log(JSON.stringify({ ok: true, pages: geometry.page_count, overflows: 0 }));
} catch (error) {
  console.error(error.message);
  process.exitCode = 1;
} finally {
  if (browser) await browser.close();
}
