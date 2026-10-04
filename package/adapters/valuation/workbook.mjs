// Optional artifact-tool authoring engine. Portable discovery, no checkout paths.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
const require=createRequire(import.meta.url);
const location=process.env.VALUATION_ARTIFACT_TOOL || require.resolve('@oai/artifact-tool');
const {Workbook,SpreadsheetFile}=await import(pathToFileURL(location).href);
const [specPath,out]=process.argv.slice(2);
const spec=JSON.parse(await fs.readFile(specPath,'utf8'));
const wb=Workbook.create();
for(const tab of spec.sheets){
 const ws=wb.worksheets.add(tab.name); ws.showGridLines=false;
 for(const row of tab.rows){
  for(const [index,value] of row.values.entries()){
   if(value===null)continue;
   const cell=ws.getCell(row.row-1,index);
   // Formula text is emitted only by the calculation graph, never input strings.
   if(index===1&&row.formula)cell.formulas=[[row.formula]];
   else cell.values=[[value]];
  }
 }
 const end=Math.max(...tab.rows.map(r=>r.row));
 ws.getRange(`A1:H${end}`).format.font={name:'Arial',size:10};
 ws.getRange(`A1:A${end}`).format.columnWidth=52;
 ws.getRange(`B1:B${end}`).format.columnWidth=22;
 ws.getRange(`C1:C${end}`).format.columnWidth=24;
 ws.getRange(`D1:H${end}`).format.columnWidth=44;
 ws.getRange(`A4:H4`).format={fill:'#193C47',font:{color:'#FFFFFF',bold:true}};
 ws.getRange(`A1:H${end}`).format.rowHeight=22;
 ws.getRange(`A1:H3`).format.rowHeight=28;
 ws.getRange(`A1:H3`).format.font={name:'Arial',size:10};
 if(end>=5){
  ws.getRange(`B5:B${end}`).setNumberFormat('#,##0.00;(#,##0.00);"-"');
  for(const row of tab.rows.filter(r=>r.row>=5)){
   const cell=ws.getRange(`B${row.row}`);
   if(row.unit==='ratio')cell.setNumberFormat('0.00%');
   if(row.unit==='shares')cell.setNumberFormat('#,##0');
   cell.format.font={color:tab.name==='Evidence'?'#444444':row.formula?'#008000':'#0000FF'};
   if(tab.name==='Checks')cell.setNumberFormat('#,##0.00;(#,##0.00);0.00');
   if(tab.name==='Evidence'&&typeof row.values[1]==='string'){
    cell.format.wrapText=true;
    ws.getRange(`A${row.row}:H${row.row}`).format.rowHeight=Math.max(22,Math.ceil(row.values[1].length/26)*14+8);
   }
  }
 }
 ws.freezePanes.freezeRows(4);
}
wb.recalculate();
const audit=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!|#NULL!',options:{useRegex:true,maxResults:500},summary:'Formula error scan'});
await fs.writeFile(path.join(out,'artifact-engine-inspection.ndjson'),audit.ndjson);
const file=await SpreadsheetFile.exportXlsx(wb);await file.save(path.join(out,'valuation.xlsx'));
const reopened=await SpreadsheetFile.importXlsx(new Uint8Array(await fs.readFile(path.join(out,'valuation.xlsx'))));
reopened.recalculate();
const checks=[];
for(const tab of spec.sheets){
 const sheet=reopened.worksheets.getItem(tab.name);
 for(const row of tab.rows.filter(r=>r.formula)){
  const actual=sheet.getRange(`B${row.row}`).values[0][0];
  if(typeof actual!=='number'||Math.abs(actual-row.expected)>1e-7*Math.max(1,Math.abs(row.expected)))
   checks.push({sheet:tab.name,cell:`B${row.row}`,expected:row.expected,actual});
 }
}
const previews=[];
for(const tab of spec.sheets){
 try{
  const image=await reopened.render({sheetName:tab.name,range:`A1:C${Math.min(Math.max(...tab.rows.map(r=>r.row)),22)}`,scale:1,format:'png'});
  const name=`workbook-${tab.name}.png`;
  await fs.writeFile(path.join(out,name),new Uint8Array(await image.arrayBuffer()));previews.push(name);
 }catch(error){previews.push({sheet:tab.name,error:String(error)});}
}
await fs.writeFile(path.join(out,'artifact-engine-checks.json'),JSON.stringify({engine:'artifact-tool',recalculated:true,saved:true,reopened:true,comparison_failures:checks,previews,scope:'All formula cells compared to Python calculation graph; previews limited to first 22 rows of each sheet. Not a financial review.'},null,2));
if(checks.length)throw Error('Reopened artifact workbook differs from model: '+JSON.stringify(checks.slice(0,3)));
