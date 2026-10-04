import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
try{
 const {chromium}=require(process.env.REPORT_OUTFIT_PLAYWRIGHT||'playwright');
 const launch={headless:true};
 if(process.env.REPORT_OUTFIT_CHROME)launch.executablePath=process.env.REPORT_OUTFIT_CHROME;
 else if(process.platform==='darwin')launch.channel='chrome';
 const browser=await chromium.launch(launch);
 try{
  const page=await browser.newPage();await page.setContent('<p>PDF capability probe</p>');
  const bytes=await page.pdf({format:'A4'});
  if(bytes.subarray(0,5).toString()!=='%PDF-')throw Error('No PDF bytes');
  console.log(JSON.stringify({engine:'Playwright Chromium',browser:browser.version(),launch_tested:true,pdf_bytes_tested:true}));
 }finally{await browser.close();}
}catch(error){console.error(String(error));process.exitCode=1;}
