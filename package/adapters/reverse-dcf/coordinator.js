// Native host orchestration. Read by a fresh coordinator and executed in functions.exec.
// Replace @OUT@ and @ROOT@ with JSON string literals before execution.
const OUT = @OUT@;
const ROOT = @ROOT@;
const PY = '@PY@';
const ENV = '@ENV@';
const sh = v => "'" + String(v).replace(/'/g, "'\\''") + "'";
const cmd = args => 'PROFESSIONAL_REPORTS_ENV='+sh(ENV)+' '+sh(PY)+' '+sh(ROOT+'/pr/report_path.py')+' --release '+sh(ROOT)+' '+args.map(sh).join(' ');
async function shell(command, escalate=false, protocol=false) {
  let r = await tools.exec_command({cmd:command,workdir:'/private/tmp',max_output_tokens:protocol?13000:1800,yield_time_ms:1000,
    ...(escalate ? {sandbox_permissions:'require_escalated',justification:'Use the user-approved existing report specimen renderer to generate this new report PDF.'}: {})});
  while (r.session_id) r = await tools.write_stdin({session_id:r.session_id,chars:'',yield_time_ms:1000,max_output_tokens:protocol?13000:1800});
  if (r.exit_code !== 0) throw Error('Command failed: '+r.output.slice(-1800));
  return r.output;
}
// Structured dispatch is consumed inside this script, not printed to the model.
// A summary cap must never truncate a protocol JSON response.
const get = async name => JSON.parse(await shell(sh(PY)+' -c '+sh('import pathlib,json;d=json.loads(pathlib.Path('+JSON.stringify(OUT+'/'+name)+').read_text());print(json.dumps('+(name==='attempt.json'?'{k:d[k] for k in ("attempt_id","requested_epoch")}':'d')+',ensure_ascii=False))'),false,true));
const sha = async name => (await shell(sh(PY)+' -c '+sh('import hashlib,pathlib;print(hashlib.sha256(pathlib.Path('+JSON.stringify(OUT+'/'+name)+').read_bytes()).hexdigest())'))).trim();
let active = null;
const dispatch = await get('dispatch.json');
const attempt = await get('attempt.json');
async function receipt(role,kind,tool,request,response,extra={}) {
  const envelope = {tool,captured_at:new Date().toISOString(),request,response,...extra};
  await shell(cmd(['receipt',OUT,role+'-'+kind,JSON.stringify(envelope)]));
}
async function worker(role) {
  const overallDeadline=(attempt.requested_epoch+585)*1000;
  // Reserve actual downstream rendering/review/closure time, not a fixed stage duration.
  const deadline=overallDeadline-(role==='author'?195000:12000);
  if (Date.now()+10000>=deadline) throw Error('Insufficient remaining report time for '+role);
  const request={fork_context:false,reasoning_effort:'high',message:dispatch[role+'_prompt']};
  const spawned=await tools.multi_agent_v1__spawn_agent(request); active=spawned.agent_id;
  await receipt(role,'spawn','multi_agent_v1__spawn_agent',request,spawned);
  let result;
  while (Date.now()+10000<deadline) {
    const waitRequest={targets:[active],timeout_ms:Math.min(60000,Math.floor(deadline-Date.now()))};
    result=await tools.multi_agent_v1__wait_agent(waitRequest);
    const status=result.status[active];
    if (status && typeof status==='object' && 'completed' in status) {
      const artifacts={};
      for(const name of (role==='author'?['input.json','argument-record.json']:['review.json'])) artifacts[name]=await sha(name);
      await receipt(role,'result','multi_agent_v1__wait_agent',waitRequest,result,{attempt_id:attempt.attempt_id,artifacts,
        ...(role==='author'?{fresh_generation:true,no_previous_report_read:true,attestation_scope:'Caller requested exact fresh-generation prompt; actual agent completion retained. Not cryptographic read-scope proof.'}: {})});
      const closeRequest={target:active}; const closed=await tools.multi_agent_v1__close_agent(closeRequest);
      await receipt(role,'close','multi_agent_v1__close_agent',closeRequest,closed); active=null; return;
    }
    if (status && status!=='running' && status!=='pending_init') throw Error('Worker terminal without completion: '+JSON.stringify(status));
  }
  throw Error('Stage deadline reached; preserve incomplete output');
}
try {
  await worker('author');
  await shell(cmd(['build',OUT]),true);
  await worker('reviewer');
  text({status:'ready-for-parent-finish',out:OUT,attempt_id:attempt.attempt_id});
} catch(error) {
  if(active) {const closeRequest={target:active}; const response=await tools.multi_agent_v1__close_agent(closeRequest);
    await shell(sh(PY)+' -c '+sh('import json,pathlib;pathlib.Path('+JSON.stringify(OUT+'/incomplete-worker-close.json')+').write_text('+JSON.stringify(JSON.stringify({request:closeRequest,response}))+')'));}
  await shell(sh(PY)+' -c '+sh('import json,pathlib;pathlib.Path('+JSON.stringify(OUT+'/coordinator-error.json')+').write_text('+JSON.stringify(JSON.stringify({error:String(error),at:new Date().toISOString()}))+')'));
  text({status:'incomplete',out:OUT,error:String(error)});
}
