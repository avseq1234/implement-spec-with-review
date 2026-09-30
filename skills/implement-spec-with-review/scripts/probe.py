#!/usr/bin/env python3
"""Read-only capability probe. Never read credential contents or silently install a provider."""
import json
import os
from pathlib import Path
import shutil
import subprocess
from core import Stop, process_start

def command(argv):
    try:
        p=subprocess.run(argv,capture_output=True,text=True,timeout=15)
        return {'exit_code':p.returncode,'output':p.stdout+p.stderr}
    except (OSError,subprocess.TimeoutExpired) as e: return {'unavailable':str(e)}

def main():
    result={'codex':{},'claude':{}}
    for name in result:
        path=shutil.which(name); r=result[name]; r['path']=path
        if not path: r['availability']='CLI_NOT_FOUND'; continue
        r['version']=command([path,'--version']); r['help']=command([path,'--help'])
        if name=='codex':
            r['exec_help']=command([path,'exec','--help']); r['resume_help']=command([path,'exec','resume','--help'])
            r['auth_status']=command([path,'login','status'])
            cache=Path(os.environ.get('CODEX_HOME',str(Path.home()/'.codex')))/'models_cache.json'
            if cache.exists():
                data=json.loads(cache.read_text()); r['cache_fetched_at']=data.get('fetched_at')
                r['models']=[{k:m[k] for k in ('slug','display_name','supported_reasoning_levels','input_modalities','context_window') if k in m} for m in data.get('models',[])]
        r['availability']='HELP_VERIFIED_REAL_INVOCATION_REQUIRED'
    try:
        result['runtime']={'process_inspection':'AVAILABLE','start_time':process_start(os.getpid())}
    except Stop as error:
        result['runtime']={'process_inspection':'BLOCKED','error':str(error),
                           'next':'Use the host tool approval mechanism for the authorized runner environment, then repeat preflight there before invoking a provider. Never disable process identity or sandbox checks.'}
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__': main()
