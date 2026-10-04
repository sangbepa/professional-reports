import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {createHash} from 'node:crypto';
const require=createRequire(import.meta.url);
let playwright;
for(const location of [process.env.REPORT_OUTFIT_PLAYWRIGHT,'playwright','../valuation-workbench/node_modules/playwright',path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')].filter(Boolean)){
 try{playwright=require(location);break;}catch{}
}
if(!playwright)throw Error('Install dependencies with npm ci in report-outfit, or set REPORT_OUTFIT_PLAYWRIGHT.');
const roots=process.argv.slice(2).map(x=>path.resolve(x));
const launch={headless:true};
if(process.env.REPORT_OUTFIT_CHROME)launch.executablePath=process.env.REPORT_OUTFIT_CHROME;
else if(process.platform==='darwin')launch.channel='chrome';
const browser=await playwright.chromium.launch(launch);
try{
 for(const root of roots){
 try{
 const page=await browser.newPage({viewport:{width:1280,height:960},deviceScaleFactor:1});
 await page.goto(pathToFileURL(path.join(root,'report.html')).href);
 if(await page.locator('body.full-report').count())await page.waitForFunction(()=>window.reportOutfit?.ready);
 await page.evaluate(()=>document.fonts.ready);
 await page.emulateMedia({media:'print'});
 const check=await page.evaluate(()=>{
  const pages=[...document.querySelectorAll('.page')].map(s=>{
   const f=s.querySelector('footer').getBoundingClientRect(),r=s.getBoundingClientRect();
   const content=[...s.querySelectorAll('.page-body h1,.page-body p,.page-body table,.page-body article,.source-entry,.spec-list>div,.three,.pair,.swatches,.grid-sample,.metric-row,.legend,.data-chart,.cover-titles,.cover-details,.cover-details>div,.cover-meta,.page-heading')];
   const overflow=content.map(e=>({tag:e.tagName,cls:e.className,fullBleed:e.matches('.cover-details')&&s.classList.contains('cover'),box:e.getBoundingClientRect(),text:e.textContent.slice(0,80)})).filter(e=>e.box.bottom>f.top-9||(!e.fullBleed&&(e.box.right>r.right-10||e.box.left<r.left-1))).map(e=>({tag:e.tag,cls:typeof e.cls==='string'?e.cls:'svg',text:e.text,bottom:e.box.bottom-r.top,footer:f.top-r.top}));
   const horizontal=[...s.querySelectorAll('h1,h3,p,td,th,.metric-value')].filter(e=>e.scrollWidth>e.clientWidth+2).map(e=>e.textContent.slice(0,80));
   const svgCollisions=[];
   for(const svg of s.querySelectorAll('.data-chart')){
    const texts=[...svg.querySelectorAll('text')];
    for(let i=0;i<texts.length;i++)for(let j=i+1;j<texts.length;j++){
     const a=texts[i].getBoundingClientRect(),b=texts[j].getBoundingClientRect();
     if(Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2)svgCollisions.push([texts[i].textContent,texts[j].textContent]);
    }
   }
   return {page:Number(s.dataset.page),id:s.id,nativePage:Number(s.dataset.nativePage||s.dataset.page),overflow,horizontal,svgCollisions};
  });
  return {pages,composition:window.reportOutfit||null,fontsReady:document.fonts.check('14px "Open Sans"'),missingImages:[...document.images].filter(i=>!i.complete||!i.naturalWidth).length,cells:[...document.querySelectorAll('[data-cell]')].map(x=>({id:x.dataset.cell,text:x.textContent})),chartValues:[...document.querySelectorAll('[data-chart-value]')].map(x=>({series:Number(x.dataset.series),category:Number(x.dataset.category),value:Number(x.dataset.chartValue)})),paragraphs:[...document.querySelectorAll('.page-body p,.page-body blockquote')].map(x=>x.textContent),brokenLinks:[...document.querySelectorAll('a[href^="#"]')].filter(a=>!document.querySelector(a.getAttribute('href'))).map(a=>a.getAttribute('href'))};
 });
 check.passed=check.fontsReady&&!check.missingImages&&!check.brokenLinks.length&&!check.composition?.failures?.length&&check.pages.every(p=>!p.overflow.length&&!p.horizontal.length&&!p.svgCollisions.length);
 await fs.writeFile(path.join(root,'layout-checks.json'),JSON.stringify(check,null,2));
 const rendered=await page.evaluate(()=>{const n=document.documentElement.cloneNode(true);n.querySelectorAll('script').forEach(x=>x.remove());return '<!doctype html>'+n.outerHTML;});
 await fs.writeFile(path.join(root,'rendered.html'),rendered);
 if(check.composition){const spec=JSON.parse(await fs.readFile(path.join(root,'specification.json'),'utf8'));spec.planned_pages=spec.planned_pages||spec.pages;spec.pages=check.pages.length;spec.actual_layout=check.pages.map(p=>({page:p.page,id:p.id,nativePage:p.nativePage}));await fs.writeFile(path.join(root,'specification.json'),JSON.stringify(spec,null,2));}
 if(check.composition){await fs.mkdir(path.join(root,'browser-pages'),{recursive:true});const ps=page.locator('.page');for(let i=0;i<await ps.count();i++)await ps.nth(i).screenshot({path:path.join(root,'browser-pages',`page-${String(i+1).padStart(3,'0')}.png`)});}
 if(!check.passed)throw Error('Layout failed: '+JSON.stringify(check.pages.filter(p=>p.overflow.length||p.horizontal.length||p.svgCollisions.length)));
 await page.pdf({path:path.join(root,'report.pdf'),printBackground:true,preferCSSPageSize:true,tagged:true});
 await page.emulateMedia({media:'screen'});
 await page.locator('.reader').evaluate(e=>e.style.display='none');
 await page.locator('.page').first().screenshot({path:path.join(root,'cover.png')});
 const summary=page.locator('.summary,.memo-opening,#conclusion');
 if(await summary.count())await summary.first().screenshot({path:path.join(root,'summary.png')});
 else await page.locator('.page').nth(Math.min(2,check.pages.length-1)).screenshot({path:path.join(root,'summary.png')});
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>document.body.classList.add('continuous'));
 const mobile=await page.evaluate(()=>({viewport:innerWidth,bodyWidth:document.body.scrollWidth,overflow:document.body.scrollWidth>innerWidth+2}));
 await fs.writeFile(path.join(root,'mobile-checks.json'),JSON.stringify(mobile,null,2));
 if(check.composition){const artifacts={};async function capture(relative){const file=path.join(root,relative),stat=await fs.stat(file);if(stat.isDirectory()){for(const child of await fs.readdir(file))await capture(path.join(relative,child));}else artifacts[relative]=createHash('sha256').update(await fs.readFile(file)).digest('hex');}for(const f of ['report.html','rendered.html','report.pdf','layout-checks.json','mobile-checks.json','specification.json','input.json','assets'])await capture(f);await fs.writeFile(path.join(root,'render-seal.json'),JSON.stringify({schema_version:1,artifacts,scope:'Native generator artifacts, copied CSS/JS/fonts; independent review remains separate.'},null,2));}
 console.log(JSON.stringify({root,pages:check.pages.length,passed:check.passed,mobile}));
 await page.close();
 }catch(error){console.error(root+' '+error.message);process.exitCode=1;}
 }
}finally{await browser.close();}
