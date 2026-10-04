/* Native A/B/C reports with measured continuation pages and repeated table headers. */
(async()=>{
 await Promise.all([document.fonts.load('14px "Open Sans"'),document.fonts.load('14px "Nanum Gothic"')]);await document.fonts.ready;
 const failures=[],original=[...document.querySelectorAll('.page:not(.cover)')];
 function fits(p){const body=p.querySelector('.page-body'),f=p.querySelector('footer').getBoundingClientRect();return [...body.children].every(e=>e.getBoundingClientRect().bottom<f.top-14);}
 function adjust(p){for(const svg of p.querySelectorAll('.data-chart')){const scale=svg.getBoundingClientRect().width/svg.viewBox.baseVal.width;for(const t of svg.querySelectorAll('text')){const n=parseFloat(getComputedStyle(t).fontSize);t.style.fontSize=Math.max(n,10.67/scale)+'px';}}}
 for(const source of original){
  const queue=[...source.querySelector('.page-body').children];source.querySelector('.page-body').replaceChildren();let page=source,part=0;
  function next(){part++;const p=source.cloneNode(true);p.id=source.id+'-continued-'+part;p.dataset.continuation=part;p.querySelector('.page-body').replaceChildren();p.querySelector('.page-heading').insertAdjacentHTML('beforeend','<div class="continuation-note">계속 · '+part+'</div>');page.after(p);page=p;}
  while(queue.length){
   const block=queue.shift(),body=page.querySelector('.page-body');body.append(block);adjust(page);
   if(fits(page))continue;
   const table=block.tagName==='TABLE'?block:block.querySelector('table');
   if(table&&table.tBodies.length&&table.tBodies[0].rows.length<=8&&body.children.length>1){block.remove();queue.unshift(block);next();continue;}
   if(table&&table.tBodies.length&&table.tBodies[0].rows.length>1){
    const remainder=block.cloneNode(true),rt=remainder.tagName==='TABLE'?remainder:remainder.querySelector('table');[...rt.tBodies[0].rows].forEach(r=>r.remove());const moved=[];
    while(!fits(page)&&table.tBodies[0].rows.length>1){moved.unshift(table.tBodies[0].lastElementChild);table.tBodies[0].lastElementChild.remove();}
    if(fits(page)&&moved.length){for(const r of moved)rt.tBodies[0].append(r);queue.unshift(remainder);next();continue;}
    for(const r of moved)table.tBodies[0].append(r);
   }
   block.remove();
   if(body.children.length){queue.unshift(block);next();continue;}
   failures.push({section:source.id,kind:'unbreakable-content',text:block.textContent.slice(0,90)});body.append(block);break;
  }
 }
 const pages=[...document.querySelectorAll('.page')];pages.forEach((p,i)=>{p.dataset.page=i+1;p.querySelector('footer b').textContent=String(i+1).padStart(2,'0')+' / '+String(pages.length).padStart(2,'0');});
 document.querySelectorAll('[data-section-link]').forEach(e=>{const t=document.getElementById(e.dataset.sectionLink);e.textContent=t?String(t.dataset.page).padStart(2,'0'):'';});
 window.reportOutfit={ready:true,failures,pages:pages.length};
})().catch(e=>window.reportOutfit={ready:true,failures:[{kind:'composition-error',message:e.message}]});
