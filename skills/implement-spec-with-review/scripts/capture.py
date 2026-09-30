#!/usr/bin/env python3
"""Execute approved test argv and produce an isolated evidence receipt (not canonical logs)."""
import argparse
import json
from pathlib import Path
import subprocess
import os
import signal
import sys
import time
import uuid
from core import stop_process_group, atomic, encoded, snapshot, digest, require

def capture(repo, spool, phase, gate, argv, timeout, expected='', invocation=None):
    require(phase in ('red','green','gate','baseline','test-after'),'Unknown evidence phase')
    require(argv and all(isinstance(x,str) for x in argv),'Command must be argv')
    start=time.time(); before=snapshot(repo); eid=uuid.uuid4().hex
    proc=subprocess.Popen(argv,cwd=repo,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
    try:
        out,err=proc.communicate(timeout=timeout)
        code=proc.returncode; output=out+b'\n'+err; timed_out=False
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid,signal.SIGTERM)
        try: out,err=proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(proc.pid,signal.SIGKILL); out,err=proc.communicate(timeout=10)
        code=124; output=out+b'\n'+err; timed_out=True
    except BaseException:
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGKILL); proc.communicate(timeout=10)
        raise
    stop_process_group(proc.pid)
    after=snapshot(repo)
    text=output.decode(errors='replace')
    invalid_red=any(s in text for s in ('SyntaxError','ImportError','ModuleNotFoundError','command not found','ERROR:'))
    red_expected=bool(phase=='red' and code!=0 and expected and expected in text and not invalid_red and not timed_out)
    receipt={'id':eid,'invocation':invocation,'phase':phase,'gate':gate,'argv':argv,'exit_code':code,
             'started_at':start,'finished_at':time.time(),'duration_seconds':time.time()-start,
             'snapshot':before['digest'],'after_snapshot':after['digest'],'red_expected':red_expected,
             'expected_failure':expected,'timeout':timed_out,'output_sha256':digest(output),'output_file':eid+'.txt'}
    spool=Path(spool); spool.mkdir(parents=True,exist_ok=True)
    atomic(spool/(eid+'.txt'),output); atomic(spool/(eid+'.json'),encoded(receipt))
    return receipt,text

def main():
    a=argparse.ArgumentParser(); a.add_argument('--context',required=True); a.add_argument('--phase',choices=['red','green','test-after'],required=True)
    a.add_argument('--gate',required=True); a.add_argument('--expected',default=''); args=a.parse_args()
    c=json.loads(Path(args.context).read_text()); g=next((g for g in c['gates'] if g['id']==args.gate),None)
    require(g,'Only approved gate commands can be executed')
    r,text=capture(c['repo'],c['spool'],args.phase,args.gate,g['argv'],c['timeout'],args.expected,c['invocation'])
    print(text); print(json.dumps(r)); return r['exit_code']
if __name__=='__main__': sys.exit(main())
