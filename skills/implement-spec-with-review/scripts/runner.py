#!/usr/bin/env python3
"""Command-oriented runner for Codex App management subagents; no autonomous shell framework."""
from __future__ import annotations
import argparse
import contextlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time
import uuid
from core import (process_start, stop_process_group, git, Run, Stop, require, atomic, encoded, read_json, snapshot, digest, lock, utc, validate_config, validate_report)
from adapters import build_argv, parse_output
from capture import capture

ROOT=Path(__file__).resolve().parents[1]

def redact(text):
    text=re.sub(r'\b(?:sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9_]{16,}|github_pat_[A-Za-z0-9_]{16,})\b','[REDACTED]',text)
    return re.sub(r'(?i)(authorization\s*:\s*bearer\s+)\S+',r'\1[REDACTED]',text)

def immutable_copy(repo,target,snap):
    target=Path(target); target.mkdir(parents=True,exist_ok=True)
    for name,meta in snap['files'].items():
        if meta.get('deleted'): continue
        source=Path(repo)/name; dest=target/name
        require(not source.is_symlink(),'Reviewer snapshot contains symlink; clarify safe materialization: '+name)
        dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(source,dest)
    subprocess.run(['git','init','-q',str(target)],check=True,timeout=30)
    subprocess.run(['git','-C',str(target),'add','--force','--all'],check=True,timeout=30)
    return target

def process(argv,cwd,prompt,timeout,heartbeat,on_start,on_beat,inherited_fds=()):
    start=time.monotonic(); proc=subprocess.Popen(argv,cwd=cwd,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True,pass_fds=inherited_fds)
    sent=False; timed_out=False
    try:
        on_start(proc.pid)
        while True:
            remaining=timeout-(time.monotonic()-start)
            if remaining<=0: timed_out=True; break
            try:
                out,err=proc.communicate(input=prompt.encode() if not sent else None,timeout=min(heartbeat,remaining)); break
            except subprocess.TimeoutExpired:
                sent=True; on_beat(proc.pid,time.monotonic()-start)
        if timed_out:
            os.killpg(proc.pid,signal.SIGTERM)
            try: out,err=proc.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL); out,err=proc.communicate(timeout=10)
    except BaseException:
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGTERM)
            try: proc.communicate(timeout=3)
            except subprocess.TimeoutExpired: os.killpg(proc.pid,signal.SIGKILL); proc.communicate(timeout=10)
        raise
    stop_process_group(proc.pid)
    return {'exit_code':proc.returncode,'stdout':out.decode(errors='replace'),'stderr':err.decode(errors='replace'),
            'timeout':timed_out,'duration_seconds':time.monotonic()-start,'pid':proc.pid}

def prompt_for(run,tid,plan,work,snap,context_file):
    s=run.state; t=run.task(tid)
    review=plan['role']=='reviewer'; independent=review and plan['kind']=='review' and plan['fresh']
    template=(ROOT/'templates'/('reviewer.md' if review else 'implementer.md')).read_text()
    documents=[]
    if review:
        docdir=work/'_spec_inputs'; require(not docdir.exists(),'Reserved review input directory collides with source; choose a confirmed mapping')
        docdir.mkdir()
        for i,d in enumerate(s['manifest']['documents']):
            dest=docdir/(str(i)+'-'+Path(d['path']).name); shutil.copy2(d['path'],dest)
            documents.append({'path':str(dest),'kind':d['kind'],'sha256':d['sha256']})
    else:
        documents=s['manifest']['documents']
    decisions=s['decisions']
    if independent:
        decisions=[d for d in decisions if d.get('category','plan') in ('plan','requirement')]
    verification=[]
    evidence_set=list(t['evidence'])
    if tid=='_final':
        for dep in t['spec'].get('dependencies',[]): evidence_set.extend(dict(e,source_task=dep) for e in run.task(dep)['evidence'])
    for e in evidence_set:
        entry={k:v for k,v in e.items() if k not in ('path','output_file')}
        if review and e.get('path'):
            target=work/'_spec_inputs'/('evidence-'+e['id']+'.txt')
            shutil.copy2(run.path/e['path'],target); entry['evidence_file']=str(target)
        verification.append(entry)
    packet={'task':t['spec'],'documents':documents,'constraints':s['manifest'].get('constraints',[]),'snapshot':snap['digest'],
            'verification_evidence':verification,
            'tdd_note':'Policy permits disclosed test-after; actual receipts below determine whether THIS implementation was test-first.',
            'phase':'independent' if independent else ('reconcile' if plan['kind']=='reconcile' else plan['kind']),
            'decisions':decisions,'required_decision_version':len(s['decisions']),
            'dependency_contracts':[{ 'id':x,'acceptance':run.task(x)['spec']['acceptance'],
                                    'summary':run.task(x)['implementation']['report']['summary'] if run.task(x)['implementation'] else ''}
                                   for x in t['spec'].get('dependencies',[])],
            'capture_command':[sys.executable,str(ROOT/'scripts/capture.py'),'--context',str(context_file)],
            'cumulative_diff':git(s['repo'],'diff','--no-ext-diff','--binary','HEAD').decode(errors='replace') if git(s['repo'],'rev-list','--all').strip() else 'No committed baseline; inspect all candidate files',
            'candidate_files':snap['files'],
            'quality_gates':t['spec']['gates'],'tdd_exception':tid in s['config']['tdd_exceptions']}
    if not independent:
        packet['finding_ledger']=t['findings']
        if plan['kind']=='reconcile': packet['independent_findings']=t['independent']['report']
    return template+'\n\nINPUT PACKET\n'+json.dumps(packet,ensure_ascii=False,indent=2)+'\n'

def import_receipts(run,tid,spool,invocation):
    t=run.task(tid)
    for p in sorted(Path(spool).glob('*.json')):
        r=read_json(p)
        require(r.get('invocation')==invocation,'Evidence invocation mismatch')
        require(r.get('phase') in ('red','green','test-after'),'Unexpected evidence phase')
        gate=next((g for g in t['spec']['gates'] if g['id']==r.get('gate')),None)
        require(gate and r.get('argv')==gate['argv'],'Evidence command outside approved gates')
        raw=(p.parent/r['output_file']).read_bytes(); require(digest(raw)==r['output_sha256'],'Evidence output checksum mismatch')
        require(r['after_snapshot']==r['snapshot'],'Test changed code; evidence invalid')
        if r['phase']=='red' and not r['red_expected']:
            r['rejected_red_reason']='Not valid missing-behavior RED; preserve evidence, do not claim test-first'
        dest=run.path/t['path']/f"round-{t['round']+1:02d}"/'tests'; dest.mkdir(parents=True,exist_ok=True)
        safe=redact(raw.decode(errors='replace')).encode(); atomic(dest/r['output_file'],safe)
        r['output_sha256']=digest(safe); r['path']=str((dest/r['output_file']).relative_to(run.path))
        atomic(dest/p.name,encoded(r)); t['evidence'].append(r)
    if t['evidence']: run.commit('test_receipts',{'task':tid,'invocation':invocation,'evidence':t['evidence']})

def invoke(run,tid,kind):
    with run.transaction():
        # Check before spending a call, clearing context, or starting any provider.
        process_start(os.getpid())
        t=run.task(tid); plan=run.plan_call(tid,kind); s=run.state
        failure_key=kind+':'+str(plan['round'])
        require(t['infra_failures'].get(failure_key,0)<=s['config']['limits']['retry_limit'],'Infrastructure retry budget exhausted')
        require(s['active'] is None,'Previous invocation requires recovery')
        with lock(Path(s['common_git_dir'])/'spec-run-writer.lock') as writer_fd:
            snap=snapshot(s['repo']); iid=uuid.uuid4().hex
            idir=run.path/t['path']/f"round-{plan['round']:02d}"/iid; idir.mkdir(parents=True)
            reviewer=plan['role']=='reviewer'
            if reviewer:
                require(snap['digest']==s['known_snapshot'],'Unaccounted candidate snapshot change before review')
                # Stable workspace per reviewer session, refreshed for each complete candidate.
                if plan['session']:
                    work=Path(plan['session'].get('worktree',''))
                    require(work.is_dir() and run.path in work.parents,'Missing reviewer isolation directory')
                    for item in list(work.iterdir()):
                        if item.name=='.git': continue
                        if item.is_dir() and not item.is_symlink(): shutil.rmtree(item)
                        else: item.unlink()
                else: work=run.path/t['path']/'review-workspaces'/iid
                immutable_copy(s['repo'],work,snap)
                isolation_snapshot=snapshot(work)['digest']
            else: work=Path(s['repo'])
            context_file=idir/'capture-context.json'; spool=idir/'spool'
            atomic(context_file,encoded({'repo':str(work),'spool':str(spool),'gates':t['spec']['gates'],
                'timeout':s['config']['limits']['timeout_seconds'],'invocation':iid}))
            prompt=prompt_for(run,tid,plan,work,snap,context_file)
            atomic(idir/'prompt.txt',redact(prompt).encode())
            output=idir/'final.json'; schema=idir/'report.schema.json'
            schema_value=read_json(ROOT/'templates/report.schema.json')
            for field in ('acceptance','coverage'): schema_value['properties'][field]['items']={'type':'string','enum':t['spec']['acceptance']}
            atomic(schema,encoded(schema_value))
            images=[d['path'] for d in s['manifest']['documents'] if d.get('kind')=='diagram']
            for image_path in images: require(Path(image_path).suffix.lower() in ('.png','.jpg','.jpeg','.webp'),'Diagram format needs a confirmed readable representation')
            argv=build_argv(dict(plan['config'],sandbox='read-only' if reviewer else 'workspace-write',images=images),work,schema,output,plan['session']['session_id'] if plan['session'] else None)
            s['metrics']['calls']+=1; t['context']=None
            t['status']='REVIEWING' if reviewer else ('FIXING' if kind=='fix' else 'IMPLEMENTING')
            s['status']=t['status']
            active={'id':iid,'task':tid,'kind':kind,'plan':plan,'before':snap,'directory':str(idir),'pid':None,'started_at':utc(),'worktree':str(work)}
            s['active']=active; s['invocations'][iid]={'status':'STARTING','task':tid,'kind':kind}
            run.checkpoint(tid,'before CLI invocation'); run.commit('invocation_start',{'task':tid,'id':iid,'role':plan['role'],'model':plan['config']['model'],'effort':plan['config']['effort'],'reason':plan['reason'],'snapshot':snap['digest'],'round':plan['round']})
            def started(pid):
                active['pid']=pid; active['process_start']=process_start(pid)
                atomic(run.path/'active-process.json',encoded(active)); run.commit('process_started',{'id':iid,'pid':pid})
            def beat(pid,elapsed): atomic(run.path/'heartbeat.json',encoded({'invocation':iid,'pid':pid,'at':utc(),'elapsed_seconds':elapsed}))
            try:
                result=process(argv,work,prompt,min(s['config']['limits']['timeout_seconds'],s['config']['limits']['active_seconds']-s['metrics']['active_seconds']),s['config']['limits']['heartbeat_seconds'],started,beat,(writer_fd,))
                s['metrics']['active_seconds']+=result['duration_seconds']
                atomic(idir/'stdout.jsonl',redact(result['stdout']).encode()); atomic(idir/'stderr.txt',redact(result['stderr']).encode())
                atomic(idir/'process.json',encoded({k:v for k,v in result.items() if k not in ('stdout','stderr')}))
                require(not result['timeout'] and result['exit_code']==0,'CLI timeout or nonzero exit; no review credit')
                parsed=parse_output(plan['config']['provider'],result['stdout'],output.read_text() if output.exists() else '')
                report=validate_report(parsed['report'],kind)
                key=run.register_session(tid,plan,parsed['session_id']); s['sessions'][key]['worktree']=str(work)
                s['sessions'][key]['decision_version']=len(s['decisions']); t['decision_version']=len(s['decisions'])
                atomic(idir/'report.json',encoded(report)); s['invocations'][iid].update(status='OUTPUT_VALIDATED',report=report,session_key=key)
                if reviewer:
                    require(snapshot(s['repo'])['digest']==snap['digest'],'Source changed during review')
                    # _spec_inputs are added by runner, exclude them from this isolation integrity check.
                    shutil.rmtree(work/'_spec_inputs',ignore_errors=True)
                    require(snapshot(work)['digest']==isolation_snapshot,'Reviewer changed isolated source; report invalid')
                    run.record_review(tid,report,key,plan['fresh'],iid,'independent' if kind=='review' and plan['fresh'] else 'complete')
                else:
                    import_receipts(run,tid,spool,iid)
                    run.accept_implementation(tid,report,iid); s['known_snapshot']=snapshot(s['repo'])['digest']
                s['invocations'][iid].update(status='COMPLETE',usage=parsed['usage'],cost=parsed['cost'],duration_seconds=result['duration_seconds'],compaction_observed=parsed['compaction_observed'])
                if parsed['compaction_observed']: run.checkpoint(tid,'compaction observed; reread originals and decisions before next call')
                s['active']=None; atomic(run.path/'active-process.json',encoded(None)); run.commit('invocation_complete',{'id':iid,'task':tid,'usage':parsed['usage'],'cost':parsed['cost'],'duration_seconds':result['duration_seconds'],'compaction_observed':parsed['compaction_observed']})
                return {'invocation':iid,'status':t['status'],'round':t['round'],'next':'reconcile' if t['independent'] else t['status']}
            except (Stop,OSError,ValueError,subprocess.SubprocessError) as e:
                s['active']=None; atomic(run.path/'active-process.json',encoded(None)); t['infra_failures'][failure_key]=t['infra_failures'].get(failure_key,0)+1
                s['invocations'][iid].update(status='FAILED',error=str(e)); run.checkpoint(tid,'invocation failed')
                # Writes may have occurred; never retry blindly. Reads can be retried within budget.
                changed=snapshot(s['repo'])['digest']!=snap['digest']
                if changed or not reviewer:
                    run.pause(tid,[{'question':'CLI invocation failed; inspect saved writes and choose recovery.','evidence':[str(e),str(idir)],
                        'options':['Resume verified session after inspection','Start a fresh authorized session after inspection','Stop this run'],'affected':[tid]}])
                elif t['infra_failures'][failure_key]>s['config']['limits']['retry_limit']:
                    t['status']='BLOCKED'; s['status']='BLOCKED'
                run.commit('invocation_failed',{'id':iid,'task':tid,'error':str(e),'changed':changed,'review_rounds':t['round']})
                raise

def gates(run,tid,phase='gate'):
    with run.transaction():
        t=run.task(tid)
        if phase!='baseline': run.ensure(tid)
        require(not run.state['active'],'Invocation still active')
        with lock(Path(run.state['common_git_dir'])/'spec-run-writer.lock'):
            for g in t['spec']['gates']:
                limits=run.state['config']['limits']; remaining=limits['active_seconds']-run.state['metrics']['active_seconds']
                require(remaining>0,'Total active-time budget exhausted')
                spool=run.path/t['path']/f"round-{t['round']+1:02d}"/'gates'
                r,output=capture(run.state['repo'],spool,phase,g['id'],g['argv'],min(remaining,limits['timeout_seconds']))
                require(r['snapshot']==r['after_snapshot'],'Gate mutated source files; evidence invalid')
                r['path']=str((spool/r['output_file']).relative_to(run.path))
                exceptions=run.state['config']['baseline_exceptions']
                r['approved_baseline']=any(x.get('task')==tid and x.get('gate')==g['id'] and x.get('output_sha256')==r['output_sha256'] for x in exceptions)
                t['evidence'].append(r); run.state['metrics']['active_seconds']+=r['duration_seconds']
                run.checkpoint(tid,phase+' evidence'); run.commit('gate_evidence',{'task':tid,'evidence':r})
            if phase=='gate' and t['implementation'] and not run.tdd_ok(tid):
                latest=t['evidence'][-len(t['spec']['gates']):]
                if all(e['exit_code']==0 for e in latest):
                    t['implementation']['validated_tdd']='test-after'
                    t['implementation']['tdd_validation_note']='No valid test-first provenance; full approved gates were run after implementation. Continue without pausing under the explicit user amendment.'
                    run.checkpoint(tid,'test-after disclosure')
                    run.commit('test_after_disclosed',{'task':tid,'validated_tdd':'test-after','reported_tdd':t['implementation']['report'].get('tdd'),'snapshot':snapshot(run.state['repo'])['digest']})
            return t['evidence'][-len(t['spec']['gates']):]

def recover(run):
    with run.transaction(), lock(Path(run.state['common_git_dir'])/'spec-run-writer.lock'):
        active=run.state['active']
        sidecar=read_json(run.path/'active-process.json') if (run.path/'active-process.json').exists() else None
        if sidecar and (not active or sidecar.get('id')==active.get('id')):
            active=sidecar
        if active:
            pid=active.get('pid'); alive=False
            if pid:
                probe=subprocess.run(['ps','-p',str(pid),'-o','lstart='],capture_output=True,text=True)
                alive=probe.returncode==0 and probe.stdout.strip()==active.get('process_start')
            require(not alive,'Old process still alive; cancel it and confirm termination before recovery')
            tid=active['task']; run.state['active']=None
            run.pause(tid,[{'question':'Interrupted invocation may have written files; saved output must be inspected before continuing.',
                'evidence':[active['directory'], 'Current snapshot: '+snapshot(run.state['repo'])['digest']],
                'options':['Inspect evidence and resume the explicit saved session','Inspect and start a fresh session','Stop'], 'affected':[tid]}])
            return {'status':'WAITING_FOR_USER','rerun':False}
        changed=run.audit(); run.render()
        return {'status':run.state['status'],'invalidated':changed,'rerun':False}

def cancel(path):
    p=Path(path)/'active-process.json'; active=read_json(p) if p.exists() else None
    if active and active.get('pid'):
        pid=active['pid']; probe=subprocess.run(['ps','-p',str(pid),'-o','lstart='],capture_output=True,text=True)
        require(probe.returncode==0 and probe.stdout.strip()==active.get('process_start'),'Process identity mismatch; refusing to signal another process')
        os.killpg(pid,signal.SIGTERM)
        for _ in range(30):
            try: os.kill(pid,0)
            except ProcessLookupError: break
            time.sleep(.1)
        else: os.killpg(pid,signal.SIGKILL)
    # Wait for owning runner to reap process before changing canonical state.
    with lock(Path(path)/'runner.lock',blocking=True):
        run=Run(path); run.state['status']='CANCELLED'
        for t in run.state['tasks'].values():
            if t['status']!='VERIFIED': t['status']='CANCELLED'
        run.state['active']=None; run.commit('cancelled',{'at':utc()})
    return {'status':'CANCELLED'}

def main():
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    a=sub.add_parser('init'); a.add_argument('--repo',required=True); a.add_argument('--config',required=True); a.add_argument('--manifest',required=True)
    for cmd in ('approve','bind','context','invoke','gates','answer','status','recover','cancel','checkpoint','invalidate-review'):
        a=sub.add_parser(cmd); a.add_argument('--run',required=True)
        if cmd in ('bind','context','invoke','gates','checkpoint','invalidate-review'): a.add_argument('--task',required=True)
        if cmd in ('approve','answer'): a.add_argument('--answer-file',required=True)
        if cmd=='answer': a.add_argument('--category',choices=['requirement','adjudication'],required=True)
        if cmd=='bind': a.add_argument('--execution-agent',required=True); a.add_argument('--review-agent',required=True); a.add_argument('--reason')
        if cmd=='context': a.add_argument('--assessment',required=True)
        if cmd=='invoke': a.add_argument('--kind',choices=['implement','fix','review','reconcile'],required=True)
        if cmd=='gates': a.add_argument('--phase',choices=['gate','baseline'],default='gate')
        if cmd in ('checkpoint','invalidate-review'): a.add_argument('--reason',required=True)
    args=p.parse_args()
    if args.command=='init':
        run=Run.create(args.repo,read_json(args.config),read_json(args.manifest)); result={'run':str(run.path),'status':run.state['status']}
    elif args.command=='cancel': result=cancel(args.run)
    else:
        run=Run(args.run)
        if args.command=='invoke': result=invoke(run,args.task,args.kind)
        elif args.command=='gates': result=gates(run,args.task,args.phase)
        elif args.command=='recover': result=recover(run)
        elif args.command=='status': result={'run':str(run.path),'status':run.state['status'],'tasks':{k:{'status':v['status'],'round':v['round'],'fallback':v['fallback']} for k,v in run.state['tasks'].items()},'pending':run.state['pending']}
        else:
            with run.transaction():
                if args.command=='approve': run.approve(Path(args.answer_file).read_text())
                elif args.command=='answer': run.answer(Path(args.answer_file).read_text(),args.category)
                elif args.command=='bind': run.bind(args.task,args.execution_agent,args.review_agent,args.reason)
                elif args.command=='context': run.context(args.task,read_json(args.assessment))
                elif args.command=='invalidate-review': run.invalidate_review(args.task,args.reason)
                elif args.command=='checkpoint': run.checkpoint(args.task,args.reason); run.commit('checkpoint',{'task':args.task,'reason':args.reason})
                result={'status':run.state['status'],'run':str(run.path)}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':
    try: main()
    except Stop as e: print(json.dumps({'status':'BLOCKED','error':str(e)},ensure_ascii=False),file=sys.stderr); sys.exit(2)
