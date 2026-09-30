#!/usr/bin/env python3
"""Deterministic external process fixture; never shipped as a real provider."""
import argparse
import json
from pathlib import Path
import sys
import time
import uuid
p=argparse.ArgumentParser(); p.add_argument('--model'); p.add_argument('--effort'); p.add_argument('--session'); p.add_argument('--output'); p.add_argument('--scenario',default='pass'); a=p.parse_args()
prompt=sys.stdin.read(); packet=json.loads(prompt.split('INPUT PACKET\n',1)[1])
if a.scenario=='timeout': time.sleep(20)
if a.scenario=='malformed': print('{broken'); sys.exit(0)
if a.scenario=='nonzero': print('failed'); sys.exit(7)
r={'status':'IMPLEMENTED','summary':'fixture result','snapshot':packet['snapshot'],'acceptance':packet['task']['acceptance'],'responses':[],
 'findings':[],'finding_updates':[],'questions':[],'coverage':packet['task']['acceptance'],'unverified':[],
 'scope_checked':['requirements','normal','boundary','error','tests','callers','interfaces','cumulative_changes','security','data_integrity','concurrency','performance','compatibility','scope'],'tdd':'test-after'}
if packet['phase'] in ('independent','review','reconcile'): r['status']='REVIEW_COMPLETE'
else:
 for fid,f in packet.get('finding_ledger',{}).items():
  if f['state'] not in ('VERIFIED_FIXED','DISMISSED_WITH_EVIDENCE'): r['responses'].append({'id':fid,'action':'ACCEPT','evidence':['fixture fix']})
if a.scenario=='question': r['status']='NEEDS_USER_INPUT'; r['questions']=[{'question':'A or B?','evidence':['spec conflict'],'options':['A: no side effect','B: another behavior'],'affected':[packet['task']['id']]}]
sid=a.session or str(uuid.uuid4()); Path(a.output).write_text(json.dumps(r)); print(json.dumps({'session_id':sid,'report':r,'usage':None}))
