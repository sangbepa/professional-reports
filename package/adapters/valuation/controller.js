// Evaluated inside a fresh native coordinator's functions.exec; not a standalone harness.
// Substitute placeholders with JSON string literals, never arbitrary shell fragments.
const OUT=@OUT@, ROOT=@ROOT@, PY=@PY@;
const sh=s=>"'"+String(s).replace(/'/g,"'\\''")+"'";
const active=new Map(), background=new Map(), stopAttempts=new Map();
let authorInputSnapshotHash=null;
async function shell(command,escalate=false,protocol=false){
 let r=await tools.exec_command({cmd:command,workdir:ROOT,max_output_tokens:protocol?15000:1000,yield_time_ms:1000,...(escalate?{sandbox_permissions:'require_escalated',justification:'Acquire public original filings without exposing credentials and use the approved report renderer within this fresh valuation clock.'}:{})});
 let output=r.output;
 while(r.session_id){r=await tools.write_stdin({session_id:r.session_id,chars:'',yield_time_ms:1000,max_output_tokens:protocol?15000:1000});output+=r.output;}
 if(r.exit_code!==0)throw Error(output.slice(-1000));return output;
}
async function read(name){return JSON.parse(await shell(sh(PY)+' -c '+sh('import pathlib;print(pathlib.Path('+JSON.stringify(OUT+'/'+name)+').read_text())'),false,true));}
async function persist(name,data){await shell(sh(PY)+' -c '+sh('import pathlib,sys; p=pathlib.Path(sys.argv[1]);f=p.open("x");f.write(sys.argv[2]);f.close()')+' '+sh(OUT+'/'+name)+' '+sh(JSON.stringify(data)));}
async function hash(name){return (await shell(sh(PY)+' -c '+sh('import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('+JSON.stringify(OUT+'/'+name)+').read_bytes()).hexdigest())'))).trim();}
const mandate=await read('mandate.json'),dispatch=await read('dispatch.json');
async function snapshot(){await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/dispatch.py')+' verify '+sh(OUT));}
async function receipt(role,kind,tool,request,response,extra={}){await persist(role+'-'+kind+'.json',{tool,request,response,captured_at:new Date().toISOString(),...extra});}
async function stop(role,agent){
 const ordinal=(stopAttempts.get(role)||0)+1;stopAttempts.set(role,ordinal);const prefix=role+(ordinal===1?'':'-retry-'+ordinal);
 const request={target:agent};await persist(prefix+'-stop-request.json',{request,requested_at:new Date().toISOString(),host_termination_confirmed:false});const response=await tools.multi_agent_v1__close_agent(request);
 await persist(prefix+'-interrupted-close.json',{request,response,captured_at:new Date().toISOString()});
 const confirmation=await tools.multi_agent_v1__wait_agent({targets:[agent],timeout_ms:10000});
 await persist(prefix+'-interrupted-status.json',{agent_id:agent,response:confirmation,captured_at:new Date().toISOString()});
 if(confirmation.status?.[agent]!=='not_found')return false;
 active.delete(role);background.delete(agent);return true;
}
async function launchAnalysisReview(){
 await snapshot();
 await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/analysis_review.py')+' '+sh(OUT));
 await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/audit_kit.py')+' '+sh(OUT));
 const role='analysis-reviewer',deadline=(mandate.requested_epoch+580)*1000;
 if(Date.now()>=deadline)throw Error('No analysis review time remaining');
 const request={fork_context:false,reasoning_effort:'high',message:dispatch[role+'_prompt']};
 const response=await tools.multi_agent_v1__spawn_agent(request);active.set(role,response.agent_id);
 background.set(response.agent_id,{role,deadline});
 await receipt(role,'spawn','multi_agent_v1__spawn_agent',request,response);
}
async function workers(specs,joinBackground=false){
 await snapshot();const watching=new Map(background),failures=[],foreground=new Set(specs.map(x=>x[0]));
 if(joinBackground)for(const value of background.values())foreground.add(value.role);
 for(const [role,reserve] of specs){
  const deadline=(mandate.requested_epoch+585-reserve)*1000;
  if(Date.now()>=deadline){failures.push(Error('Insufficient remaining time for '+role));continue;}
  if(role==='author'){
   const artifacts={};for(const name of ['valuation-input.json','model-result.json','model-verification.json'])artifacts[name]=await hash(name);
   await persist('author-input-snapshot.json',{artifacts,captured_at:new Date().toISOString(),attempt_id:mandate.attempt_id});
   authorInputSnapshotHash=await hash('author-input-snapshot.json');
   await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/author_packet.py')+' '+sh(OUT));
  }
  const request={fork_context:false,reasoning_effort:role==='author'?'medium':'high',message:dispatch[role+'_prompt']};
  const response=await tools.multi_agent_v1__spawn_agent(request);const agent=response.agent_id;
  active.set(role,agent);watching.set(agent,{role,deadline});
  await receipt(role,'spawn','multi_agent_v1__spawn_agent',request,response);
 }
 // Carry the early reviewer across phases, but do not delay publication merely
 // because it is still working. All native workers share one observed wait.
 while([...watching.values()].some(x=>foreground.has(x.role))){
  for(const [agent,{role,deadline}] of watching){
   if(role==='curator'||role==='analyst'||role==='author'){
    let terminating=false;
    try{
     let readiness=JSON.parse(await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/ready.py')+' '+sh(role)+' '+sh(OUT)+' --verify'));
     if(readiness.status==='not_ready')readiness=JSON.parse(await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/ready.py')+' '+sh(role)+' '+sh(OUT)+' --probe'));
     if(['ready_unreviewed','draft_available_unreviewed'].includes(readiness.status)){
      terminating=true;if(!await stop(role,agent))throw Error('Host termination not confirmed for '+role);
      const frozen=JSON.parse(await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/ready.py')+' '+sh(role)+' '+sh(OUT)+(readiness.status==='ready_unreviewed'?' --verify':' --probe')));
      if(!['ready_unreviewed','draft_available_unreviewed'].includes(frozen.status)||JSON.stringify(frozen.artifacts)!==JSON.stringify(readiness.artifacts))throw Error('Producer handoff not stable after host termination');
      if(role==='author'&&await hash('author-input-snapshot.json')!==authorInputSnapshotHash)throw Error('Author baseline snapshot changed after dispatch');
      await persist(role+'-handoff-accepted.json',{readiness:frozen,financial_approval:false,native_completion_claimed:false,producer_scope_complete_claimed:readiness.status==='ready_unreviewed',decision_basis:'PM selected a hash-stable, deterministically reproducible unreviewed handoff within unchanged final independent review/time gates',host_termination_receipt:role+'-interrupted-status.json'});
      if(role==='author')await persist('author-result.json',{kind:'unreviewed_artifact_handoff',attempt_id:mandate.attempt_id,author_agent_id:agent,artifacts:frozen.artifacts,input_snapshot_sha256:await hash('author-input-snapshot.json'),captured_at:new Date().toISOString(),native_completion_claimed:false,financial_approval:false,fresh_generation:true,no_previous_report_read:true,attestation_scope:'Caller scope and hash-stable files; no native completion or cryptographic read-scope claim.'});
      watching.delete(agent);continue;
     }
    }catch(error){if(terminating){watching.delete(agent);failures.push(error);continue;}}
   }
   if(Date.now()>=deadline){await stop(role,agent);watching.delete(agent);failures.push(Error('Work deadline for '+role+' reached'));}
  }
  if(![...watching.values()].some(x=>foreground.has(x.role)))break;
  // One multi-target wait avoids independent pending waits for sibling workers.
  const nearest=Math.min(...[...watching.values()].map(x=>x.deadline));
  const waitRequest={targets:[...watching.keys()],timeout_ms:Math.max(10000,Math.min(10000,Math.floor(nearest-Date.now())))};
  const result=await tools.multi_agent_v1__wait_agent(waitRequest);
  for(const [agent,{role}] of [...watching]){
   const state=result.status?.[agent];
   if(state&&typeof state==='object'&&'completed' in state){
    const artifacts={},missing=[];
    const names=role==='curator'?['requests.json','selectors.json','selection-gaps.json','accounting-evidence.json','capital-evidence.json','history-spec.json','historical-reconciliation.json']:role==='analyst'?['valuation-input.json','evidence.json','judgments.json']:role==='author'?['narrative.json','argument-record.json']:role==='analysis-reviewer'?['analysis-review.json']:role.startsWith('visual-')?[role+'-review.json']:['review.json'];
    for(const name of names){try{artifacts[name]=await hash(name);}catch(error){missing.push(name);}}
    await receipt(role,'result','multi_agent_v1__wait_agent',waitRequest,result,{attempt_id:mandate.attempt_id,artifacts,missing_artifacts:missing,...(role==='author'?{fresh_generation:true,no_previous_report_read:true,attestation_scope:'Exact caller scope instruction and native completion retained; not cryptographic read-scope proof.'}:{})});
    const closeRequest={target:agent};const closed=await tools.multi_agent_v1__close_agent(closeRequest);
    await receipt(role,'close','multi_agent_v1__close_agent',closeRequest,closed);active.delete(role);watching.delete(agent);background.delete(agent);
    if(missing.length)failures.push(Error('Missing '+role+' output: '+missing.join(',')));
    else if(role==='curator'){try{const verification=JSON.parse(await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/source_cells.py')+' '+sh(OUT)+' '+sh(OUT+'/requests.json')+' --requests --cutoff '+sh(mandate.cutoff)+' --verify'));await persist('curation-verification.json',verification);}catch(error){failures.push(error);}}
   }else if(state&&state!=='running'&&state!=='pending_init'){
    await stop(role,agent);watching.delete(agent);failures.push(Error('Terminal incomplete '+role+': '+JSON.stringify(state)));
   }
  }
 }
 if(failures.length)throw failures[0];
}
async function worker(role,reserve){await workers([[role,reserve]]);}

async function stage(name,escalate=false){await snapshot();await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/coldrun.py')+' '+sh(name)+' '+sh(OUT),escalate);}
try{
 await snapshot();
 if(!mandate.stock_code)throw Error('Explicit listed stock identity required for fresh source acquisition');
 await shell(sh(PY)+' -c '+sh('import subprocess,sys,time; remaining=min(45,float(sys.argv[3])+585-time.time()); assert remaining>0; subprocess.run([sys.argv[1],sys.argv[2],sys.argv[4],"--stock",sys.argv[5],"--cutoff",sys.argv[6]],timeout=remaining,check=True)')+' '+sh(PY)+' '+sh(ROOT+'/adapters/valuation/collect.py')+' '+sh(mandate.requested_epoch)+' '+sh(OUT)+' '+sh(mandate.stock_code)+' '+sh(mandate.cutoff),true);
 await workers([['curator',355],['analyst',235]]);await stage('model');
 await launchAnalysisReview();
 await worker('author',115);await stage('publish',true);
 await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/review_packet.py')+' '+sh(OUT));
 await shell(sh(PY)+' -c '+sh('import pathlib,json,hashlib,sys; p=pathlib.Path(sys.argv[1]); v=json.loads((p/"publication-verification.json").read_text()); names=set(v["artifacts"])|{"publication-verification.json","workbook/valuation.xlsx","evidence.json","judgments.json","calculation-graph.json"}; names.update(x.relative_to(p).as_posix() for x in (p/"sources").rglob("*") if x.is_file()); names.update(x.relative_to(p).as_posix() for x in (p/"review-frames").rglob("*") if x.is_file()); names.update(x.name for x in p.iterdir() if x.is_file() and x.suffix in {".py",".json"} and x.name not in {"reviewed-target.json","analysis-review.json","analysis-review-draft.json"}); data={"artifacts":{n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in sorted(names)},"attempt_id":sys.argv[2]}; f=(p/"reviewed-target.json").open("x");json.dump(data,f,ensure_ascii=False,indent=2);f.close()')+' '+sh(OUT)+' '+sh(mandate.attempt_id));
 await workers([['reviewer',5],['visual-left',15],['visual-right',15]],true);
 await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/trace.py')+' '+sh(OUT));
 await stage('finish');
 await shell(sh(PY)+' '+sh(ROOT+'/adapters/valuation/trace.py')+' '+sh(OUT));
 if(Date.now()/1000>mandate.requested_epoch+600)throw Error('Delivery deadline exceeded after finish');
 await persist('delivery.json',{status:'delivered',delivered_epoch:Date.now()/1000,elapsed_seconds:Date.now()/1000-mandate.requested_epoch,deadline_reset:false,completion_sha256:await hash('completion.json'),financial_review_receipt_sha256:await hash('review.json'),report_pdf_sha256:await hash('report.pdf')});
 text({status:'complete',out:OUT,attempt_id:mandate.attempt_id});
}catch(error){
 for(const [role,agent] of active)await stop(role,agent);
 await persist('attempt-result.json',{status:'incomplete',reason:String(error),elapsed_seconds:Date.now()/1000-mandate.requested_epoch,deadline_reset:false,report_completed:false,release_promoted:false,unconfirmed_live_actors:[...active.entries()]});
 text({status:'incomplete',out:OUT,error:String(error)});
}
