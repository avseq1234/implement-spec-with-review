#!/usr/bin/env python3
"""Approved read-only fixture probe: primary explicit resume and fallback fresh-session protocol.
Not an extra task/review round. Charges the existing validation run's call/time budgets.
"""
import argparse
import json
from pathlib import Path
import subprocess
import time
import uuid
from core import Run, require, atomic, encoded, lock, utc
from runner import process, redact
from adapters import build_argv, parse_output

def main():
    p=argparse.ArgumentParser(); p.add_argument('--run',required=True); a=p.parse_args()
    run=Run(a.run); records=[]; primary_id=None; marker=uuid.uuid4().hex
    with run.transaction():
        s=run.state; limits=s['config']['limits']; require(not s['active'],'Task invocation still active')
        with lock(Path(s['common_git_dir'])/'spec-run-writer.lock'):
            root=run.path/'protocol-smoke'; root.mkdir(exist_ok=True)
            schema={'type':'object','properties':{'marker':{'type':'string'},'ok':{'type':'boolean'}},'required':['marker','ok'],'additionalProperties':False}
            atomic(root/'schema.json',encoded(schema))
            for phase,role in [('primary-new','primary'),('primary-resume','primary'),('fallback-fresh','fallback')]:
                require(s['metrics']['calls']<limits['max_calls'],'Call budget exhausted')
                remaining=limits['active_seconds']-s['metrics']['active_seconds']; require(remaining>0,'Active-time budget exhausted')
                iid=uuid.uuid4().hex; directory=root/iid; directory.mkdir()
                cfg=dict(s['config']['roles'][role],sandbox='read-only')
                sid=primary_id if phase=='primary-resume' else None
                prompt=('Read-only protocol validation. Do not invoke tools or modify files. Remember the marker '+marker+' and return it with ok true.' if phase=='primary-new' else
                        'Read-only protocol validation. Do not invoke tools or modify files. Return the marker from the preceding turn in this explicit session with ok true.' if phase=='primary-resume' else
                        'Read-only fallback fresh-session protocol validation. Do not invoke tools or modify files. Return marker "fallback-fresh" and ok true.')
                argv=build_argv(cfg,s['repo'],root/'schema.json',directory/'final.json',sid)
                s['metrics']['calls']+=1
                s['active']={'id':iid,'task':'_final','kind':'protocol-probe','pid':None,'directory':str(directory),'started_at':utc()}
                run.commit('protocol_probe_started',{'id':iid,'phase':phase,'role':role,'model':cfg['model'],'effort':cfg['effort']})
                def started(pid):
                    active=s['active']; active['pid']=pid
                    active['process_start']=subprocess.run(['ps','-p',str(pid),'-o','lstart='],capture_output=True,text=True).stdout.strip()
                    atomic(run.path/'active-process.json',encoded(active)); run.commit('process_started',{'id':iid,'pid':pid})
                def beat(pid,elapsed): atomic(run.path/'heartbeat.json',encoded({'id':iid,'pid':pid,'elapsed_seconds':elapsed,'at':utc()}))
                result=process(argv,s['repo'],prompt,min(limits['timeout_seconds'],remaining),limits['heartbeat_seconds'],started,beat)
                atomic(directory/'stdout.jsonl',redact(result['stdout']).encode()); atomic(directory/'stderr.txt',redact(result['stderr']).encode())
                s['metrics']['active_seconds']+=result['duration_seconds']
                require(result['exit_code']==0 and not result['timeout'],'Protocol CLI failed; inspect evidence, no silent retry')
                parsed=parse_output(cfg['provider'],result['stdout'],(directory/'final.json').read_text())
                expected=marker if role=='primary' else 'fallback-fresh'
                require(parsed['report']=={'marker':expected,'ok':True},'Protocol result mismatch')
                if phase=='primary-new': primary_id=parsed['session_id']
                elif phase=='primary-resume': require(parsed['session_id']==primary_id,'Explicit resume changed session')
                else: require(parsed['session_id']!=primary_id,'Fallback reused primary session')
                entry={'id':iid,'phase':phase,'role':role,'model':cfg['model'],'effort':cfg['effort'],'session_id':parsed['session_id'],
                       'status':'COMPLETE','usage':parsed['usage'],'cost':parsed['cost'],'duration_seconds':result['duration_seconds']}
                records.append(entry); s.setdefault('protocol_sessions',[]).append(entry); s['invocations'][iid]=entry
                s['active']=None; atomic(run.path/'active-process.json',encoded(None)); run.commit('protocol_probe_complete',entry)
            atomic(root/'results.json',encoded(records))
    print(json.dumps(records,indent=2))
if __name__=='__main__': main()
