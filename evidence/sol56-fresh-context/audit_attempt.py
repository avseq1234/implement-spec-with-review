#!/usr/bin/env python3
"""Read-only observer audit, intentionally not supplied to the tested orchestrator."""
from pathlib import Path
import hashlib
import json
import sys

attempt_path=Path(sys.argv[1]).resolve()
attempt=json.loads(attempt_path.read_text())
skill=Path(attempt['skill']); repo=Path(attempt['fixture'])
sys.path.insert(0,str(skill/'scripts'))
from core import snapshot
run=next(repo.glob('.spec-runs/*'))
s=json.loads((run/'state.json').read_text())
frames=[json.loads(line) for line in (run/'events.jsonl').read_text().splitlines()]
for index,event in enumerate(frames,1):
    assert event['seq']==index
    encoded=json.dumps(event['state'],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    assert hashlib.sha256(encoded).hexdigest()==event['state_sha256']
assert frames[-1]['state']==s
assert s['status']=='VERIFIED' and s['active'] is None and not s['pending']
assert s['order']==['1.1','1.2','_final']
managers=[]; evidence_count=0; results={}
for tid,task in s['tasks'].items():
    assert task['status']=='VERIFIED' and 0<task['round']<=5
    managers+=list(task['agents'].values())
    review=task['review']; candidate=review['snapshot']
    assert set(task['spec']['acceptance'])<=set(review['report']['coverage'])
    assert not review['report']['questions'] and not review['report']['unverified']
    assert not any(f['blocking'] and f['state'] not in ('VERIFIED_FIXED','DISMISSED_WITH_EVIDENCE') for f in task['findings'].values())
    for evidence in task['evidence']:
        assert hashlib.sha256((run/evidence['path']).read_bytes()).hexdigest()==evidence['output_sha256']
        evidence_count+=1
    for gate in task['spec']['gates']:
        assert any(e['gate']==gate['id'] and e['phase']=='gate' and e['snapshot']==e['after_snapshot']==candidate and e['exit_code']==0 for e in task['evidence'])
    if tid!='_final':
        assert task['implementation']['snapshot']==candidate
        reds=[e for e in task['evidence'] if e['phase']=='red' and e['exit_code']!=0 and e.get('red_expected')]
        greens=[e for e in task['evidence'] if e['phase']=='green' and e['exit_code']==0 and e['snapshot']==candidate]
        assert any(r['finished_at']<g['started_at'] and r['snapshot']!=g['snapshot'] for r in reds for g in greens)
        assert task['implementation']['report']['tdd']=='test-first'
    results[tid]={'status':task['status'],'round':task['round'],'snapshot':candidate,'managers':task['agents'],'fallback':task['fallback']}
assert len(managers)==len(set(managers))==6
assert snapshot(repo)['digest']==s['known_snapshot']==s['tasks']['_final']['review']['snapshot']
for document in s['manifest']['documents']:
    assert hashlib.sha256(Path(document['path']).read_bytes()).hexdigest()==document['sha256']
assert len(s['invocations'])==s['metrics']['calls']
failed_invocations=[]
for iid,invocation in s['invocations'].items():
    if invocation['status']=='FAILED':
        failure=next(e for e in s['history'] if e['event']=='invocation_failed' and e['data']['id']==iid)
        assert failure['data']['changed'] is False
        start=next(e for e in frames if e['event']=='invocation_start' and e['data']['id']==iid)
        task_id=invocation['task']
        assert failure['data']['review_rounds']==start['state']['tasks'][task_id]['round']
        assert invocation['kind'] in ('review','reconcile')
        assert not any(e['event']=='review_complete' and e['data'].get('invocation')==iid for e in s['history'])
        failed_invocations.append({'id':iid,'task':task_id,'error':invocation['error'],'review_credit':0})
        continue
    assert invocation['status']=='COMPLETE'
    session=s['sessions'][invocation['session_key']]
    assert session['provider']=='codex' and session['model']=='gpt-5.6-sol'
    assert session['effort']=={'primary':'medium','reviewer':'high','fallback':'xhigh'}[session['role']]
for role,effort in [('primary','medium'),('reviewer','high'),('fallback','xhigh')]:
    assert s['config']['roles'][role]['effort']==effort
assert s['metrics']['calls']<=30 and s['metrics']['active_seconds']<=5400
for tid in s['order']:
    for event in [e for e in s['history'] if e['event']=='review_complete' and e['data']['task']==tid]:
        earlier=[e for e in frames if e['seq']<event['seq'] and e['event']=='independent_findings_saved' and e['data']['task']==tid][-1]
        assert earlier['state']['tasks'][tid]['independent']['session_key']==event['data']['session_key']
assert all(hashlib.sha256((skill/name).read_bytes()).hexdigest()==sha for name,sha in attempt['skill_sha256'].items())
print(json.dumps({'result':'PASS','run':str(run),'candidate_snapshot':s['known_snapshot'],'tasks':results,
    'journal_frames_verified':len(frames),'evidence_output_hashes_verified':evidence_count,
    'distinct_managers':len(set(managers)),'sessions':len(s['sessions']),'metrics':s['metrics'],
    'skill_unchanged_during_attempt':True,'failed_invocations':failed_invocations},ensure_ascii=False,indent=2))
