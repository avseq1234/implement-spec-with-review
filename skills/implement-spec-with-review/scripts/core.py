"""Small, fail-closed control plane; all canonical writes go through Run.commit."""
from __future__ import annotations
import contextlib
import copy
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import uuid

ROLES = ('primary','reviewer','fallback')
STATES = ('PENDING','READY','IMPLEMENTING','REVIEWING','FIXING','WAITING_FOR_USER','VERIFIED','BLOCKED','FAILED','CANCELLED')
SCOPE = {'requirements','normal','boundary','error','tests','callers','interfaces','cumulative_changes',
         'security','data_integrity','concurrency','performance','compatibility','scope'}
FINDING_STATES = {'OPEN','ACCEPTED','FIXED_PENDING_VERIFICATION','VERIFIED_FIXED',
                 'REBUTTED_PENDING_ADJUDICATION','DISMISSED_WITH_EVIDENCE','BLOCKED'}
CLOSED = {'VERIFIED_FIXED','DISMISSED_WITH_EVIDENCE'}

class Stop(Exception):
    """Action cannot proceed within confirmed scope."""

def utc(): return dt.datetime.now(dt.timezone.utc).isoformat()
def digest(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
def read_json(path): return json.loads(Path(path).read_text())
def require(condition, reason):
    if not condition: raise Stop(reason)

def process_start(pid):
    """Require usable process identity in the environment that will own the CLI."""
    try:
        result=subprocess.run(['ps','-p',str(pid),'-o','lstart='],capture_output=True,text=True,timeout=10)
    except (OSError,subprocess.SubprocessError) as error:
        raise Stop('Required process inspection unavailable: '+str(error)) from error
    require(result.returncode==0 and bool(result.stdout.strip()),
            'Required process inspection unavailable: ps returned no usable start time')
    return result.stdout.strip()

def atomic(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix='.'+path.name,dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.chmod(tmp,0o600); os.replace(tmp,path)
        fd=os.open(path.parent,os.O_RDONLY)
        try: os.fsync(fd)
        finally: os.close(fd)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def stop_process_group(pgid):
    """Ensure ordinary descendants cannot outlive a completed foreground invocation."""
    import signal
    try: os.killpg(pgid,signal.SIGTERM)
    except ProcessLookupError: return
    deadline=time.monotonic()+.5
    while time.monotonic()<deadline:
        try: os.killpg(pgid,0)
        except ProcessLookupError: return
        time.sleep(.02)
    try: os.killpg(pgid,signal.SIGKILL)
    except ProcessLookupError: pass


def git(repo,*args):
    p=subprocess.run(['git','-C',str(repo),*args],capture_output=True,timeout=30)
    require(p.returncode==0,'git failed: '+p.stderr.decode(errors='replace')[:500])
    return p.stdout

def snapshot(repo):
    repo=Path(repo).resolve()
    names=set(git(repo,'ls-files','-z','--cached','--others','--exclude-standard').split(b'\0'))-{b''}
    files={}
    for name in sorted(names):
        rel=os.fsdecode(name)
        if rel=='.spec-runs' or rel.startswith('.spec-runs/'): continue
        p=repo/rel
        try: st=p.lstat()
        except FileNotFoundError: files[rel]={'deleted':True}; continue
        require(not stat.S_ISDIR(st.st_mode),'Submodules/directories need an explicitly supported snapshot policy: '+rel)
        data=os.fsencode(os.readlink(p)) if p.is_symlink() else p.read_bytes()
        files[rel]={'sha256':digest(data),'mode':stat.S_IMODE(st.st_mode),'symlink':p.is_symlink(),'size':len(data)}
    return {'digest':digest(encoded(files)),'files':files}

def resolve_roles(current,previous=None,reuse=False):
    roles=copy.deepcopy(previous or {}) if reuse else {}
    for role,value in current.items():
        require(role in ROLES,'Unknown role '+role)
        roles[role]={**roles.get(role,{}),**value}
    missing=[r for r in ROLES if not all(roles.get(r,{}).get(k) is not None for k in ('provider','model','effort'))]
    return {'roles':roles,'missing':missing}

def validate_config(c):
    require(isinstance(c,dict),'config must be an object')
    require(set(c.get('roles',{}))==set(ROLES),'Three independent roles are required')
    for role,r in c['roles'].items():
        require(r.get('provider') in ('codex','claude','fake'),'Unverified provider')
        require(all(r.get(k) for k in ('model','display_name','cli','capability_evidence')),'Missing model capability evidence')
        if r['provider']=='codex': require(r['model'].startswith('gpt-'),'Codex model/provider mismatch')
        if r['provider']=='claude': require(r['model'].startswith('claude-'),'Claude model/provider mismatch')
        require('effort' in r,'Missing effort (use model-default only when explicitly verified)')
        require(r['effort'] in r.get('verified_efforts',[]),'Unsupported/unverified effort; NEEDS_USER_INPUT')
    limits=c.get('limits',{})
    for k in ('timeout_seconds','max_calls','active_seconds','heartbeat_seconds'):
        require(isinstance(limits.get(k),(float,int)) and limits[k]>0,'Missing finite positive budget '+k)
        require(limits[k]<float('inf'),'Infinite budget '+k)
    require(isinstance(limits.get('retry_limit'),int) and 0<=limits['retry_limit']<=10,'Missing finite retry limit')
    require(c.get('context_policy') in ('ask','checkpoint-resume'),'Unknown context policy')
    require(c.get('context_policy_confirmed') is True,'Context policy requires confirmation')
    require(isinstance(c.get('baseline_exceptions'),list) and isinstance(c.get('tdd_exceptions'),list),'Explicit baseline/TDD exceptions required')
    return c

def question_valid(q):
    return isinstance(q,dict) and all(q.get(k) for k in ('question','evidence','options','affected'))

def validate_report(r,kind):
    require(isinstance(r,dict),'Report must be a JSON object')
    if r.get('status')=='NEEDS_USER_INPUT':
        require(r.get('questions') and all(question_valid(q) for q in r['questions']),'Questions need evidence, options/impact and affected scope')
        return r
    require(r.get('summary') and isinstance(r.get('questions'),list),'Missing complete report fields')
    require(not r['questions'],'Unresolved questions must use NEEDS_USER_INPUT')
    if kind in ('review','reconcile'):
        require(r.get('status')=='REVIEW_COMPLETE','Missing complete review')
        require(r.get('snapshot'),'Missing reviewed snapshot')
        require(SCOPE.issubset(set(r.get('scope_checked',[]))),'Incomplete review scope')
        require(isinstance(r.get('coverage'),list) and isinstance(r.get('unverified'),list),'Missing coverage/unverified list')
        require(isinstance(r.get('findings'),list) and isinstance(r.get('finding_updates'),list),'Missing finding ledger updates')
        ids=[]
        for f in r['findings']:
            require(all(k in f for k in ('id','severity','blocking','file','line','requirement','trigger','impact','evidence','direction')),'Incomplete finding')
            require(f['severity'] in ('P0','P1','P2','P3') and isinstance(f['blocking'],bool),'Invalid severity/blocking')
            require(isinstance(f['line'],int) and f['line']>0 and all(f[k] for k in ('id','file','requirement','trigger','impact','evidence','direction')),'Unproven finding; clarify rather than assert a defect')
            ids.append(f['id'])
        require(len(ids)==len(set(ids)),'Duplicate finding IDs')
    else:
        require(r.get('status')=='IMPLEMENTED','Missing implementation report')
        require(isinstance(r.get('responses'),list) and isinstance(r.get('acceptance'),list),'Missing implementation responses/coverage')
        for x in r['responses']:
            require(x.get('action') in ('ACCEPT','REBUT','NEEDS_USER_INPUT') and x.get('id'),'Invalid finding response')
            require(x.get('evidence'),'Response needs evidence')
            require(x['action']!='NEEDS_USER_INPUT','Use NEEDS_USER_INPUT status to pause affected work')
    return r

@contextlib.contextmanager
def lock(path,blocking=False):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('a+b') as f:
        try: fcntl.flock(f,fcntl.LOCK_EX | (0 if blocking else fcntl.LOCK_NB))
        except BlockingIOError: raise Stop('Another runner holds the lock: '+str(path))
        try: yield f.fileno()
        finally: fcntl.flock(f,fcntl.LOCK_UN)

def safe_id(task): return re.sub(r'[^A-Za-z0-9_.-]+','_',task).strip('.')[:48]+'-'+digest(task.encode())[:8]

class Run:
    def __init__(self,path):
        self.path=Path(path).resolve()
        require(self.path.is_dir(),'Unknown explicit run directory')
        self.state=None
        self.load()
    @classmethod
    def create(cls,repo,config,manifest):
        repo=Path(repo).resolve(); validate_config(config)
        require(Path(os.fsdecode(git(repo,'rev-parse','--show-toplevel')).strip()).resolve()==repo,'Use repository root')
        require(manifest.get('documents') and manifest.get('tasks'),'Documents and original tasks are required')
        ids=[t['id'] for t in manifest['tasks']]
        require(len(ids)==len(set(ids)) and '_final' not in ids,'Duplicate/reserved task ID')
        seen=set()
        for t in manifest['tasks']:
            require(isinstance(t['id'],str) and t.get('acceptance') and t.get('requirements') and t.get('gates'),'Task needs original ID, requirements, acceptance and gates')
            require(set(t.get('dependencies',[]))<=seen,'Task ordering/dependencies need user clarification')
            require(isinstance(t.get('high_risk'),bool),'Explicit high-risk classification required')
            for g in t['gates']: require(g.get('id') and g.get('argv') and isinstance(g['argv'],list),'Gate needs ID and safe argv')
            seen.add(t['id'])
        require(manifest.get('final_gates'),'Final integration gates required')
        manifest=copy.deepcopy(manifest)
        for d in manifest['documents']:
            p=Path(d['path']); p=p if p.is_absolute() else repo/p
            require(p.is_file(),'Missing original document '+str(p))
            d['path']=str(p.resolve()); d['sha256']=digest(p.read_bytes())
            require(d.get('kind'),'Document kind required')
        require({'high-level','tasks','spec'}<=set(d['kind'] for d in manifest['documents']),'Missing high-level/tasks/spec inputs')
        common=Path(os.fsdecode(git(repo,'rev-parse','--path-format=absolute','--git-common-dir')).strip())
        with lock(common/'spec-run-writer.lock'):
            exclude=common/'info/exclude'; exclude.parent.mkdir(exist_ok=True)
            old=exclude.read_text() if exclude.exists() else ''
            if '/.spec-runs/' not in old.splitlines(): atomic(exclude,(old+'\n/.spec-runs/\n').encode())
            now=dt.datetime.now().astimezone(); rid=now.strftime('%Y%m%dT%H%M%S%z')+'-'+uuid.uuid4().hex[:8]
            path=repo/'.spec-runs'/rid; path.mkdir(parents=True,mode=0o700)
            obj=cls.__new__(cls); obj.path=path
            tasks={t['id']:obj.new_task(t) for t in manifest['tasks']}
            final={'id':'_final','requirements':['whole-design','cross-task-contracts'],'acceptance':['whole-design','cross-task-contracts'],
                   'dependencies':ids,'gates':manifest['final_gates'],'high_risk':False}
            tasks['_final']=obj.new_task(final)
            obj.state={'run_id':rid,'repo':str(repo),'common_git_dir':str(common),'timezone':str(now.tzinfo),'created_at':utc(),
                       'status':'PENDING','validation_mode':'SIMULATED' if any(r['provider']=='fake' for r in config['roles'].values()) else 'REAL_CLI','approved':False,'config':config,'manifest':manifest,'tasks':tasks,'order':ids+['_final'],
                       'sessions':{},'decisions':[],'events_count':0,'metrics':{'calls':0,'active_seconds':0.0,'user_wait_seconds':0.0,
                       'tokens':None,'cost':None},'pending':[],'active':None,'initial_snapshot':snapshot(repo),'invocations':{},'history':[], 'known_snapshot':snapshot(repo)['digest']}
            obj.commit('created',{'original_task_ids':ids})
        return obj
    @staticmethod
    def new_task(spec):
        return {'spec':spec,'path':('final-review' if spec['id']=='_final' else 'tasks/'+safe_id(spec['id'])),
                'status':'PENDING','round':0,'findings':{},'agents':None,'agent_history':[], 'implementation':None,
                'review':None,'independent':None,'high_risk_snapshot':None,'evidence':[], 'sessions':[],
                'checkpoint':{},'infra_failures':{},'fallback':False,'decision_version':0,'context':None}
    def load(self):
        journal=self.path/'events.jsonl'; require(journal.exists(),'Missing canonical event journal')
        lines=journal.read_bytes().splitlines(keepends=True); last=None
        for i,line in enumerate(lines):
            require(line.endswith(b'\n'),'Incomplete journal tail; recover conservatively, do not replay writes')
            try: e=json.loads(line)
            except ValueError: raise Stop('Corrupt journal; manual recovery required')
            require(e['seq']==i+1,'Journal sequence mismatch')
            require(digest(encoded(e['state']))==e['state_sha256'],'Journal state checksum mismatch')
            last=e['state']
        require(last is not None,'Empty journal'); self.state=last
    def commit(self,event,data):
        s=self.state; s['events_count']+=1
        s['history'].append({'seq':s['events_count'],'at':utc(),'event':event,'data':data})
        e={'seq':s['events_count'],'at':utc(),'event':event,'data':data,'state':s,'state_sha256':digest(encoded(s))}
        with (self.path/'events.jsonl').open('ab') as f: f.write(encoded(e)+b'\n'); f.flush(); os.fsync(f.fileno())
        self.render()
    def render(self):
        s=self.state
        for name,value in [('state.json',s),('config.json',s['config']),('manifest.json',s['manifest']),('sessions.json',s['sessions'])]: atomic(self.path/name,encoded(value)+b'\n')
        for t in s['tasks'].values():
            d=self.path/t['path']; atomic(d/'findings.json',encoded(t['findings'])+b'\n'); atomic(d/'checkpoint.json',encoded(t['checkpoint'])+b'\n')
        lines=['# Discussion',f"Run `{s['run_id']}` · timezone `{s['timezone']}`",'']
        for h in s['history']:
            lines += [f"## {h['seq']} · {h['at']} · {h['event']}", '```json',json.dumps(h['data'],ensure_ascii=False,indent=2),'```','']
        atomic(self.path/'discussion.md','\n'.join(lines).encode())
        lines=['# Decisions','']
        for d in s['decisions']: lines += [f"## Decision {d['version']} · {d['at']}", d['answer'], 'Scope: '+json.dumps(d['scope'],ensure_ascii=False), 'Questions: '+json.dumps(d.get('questions',[]),ensure_ascii=False),'']
        atomic(self.path/'decisions.md','\n'.join(lines).encode())
        lines=['# Run report',f"Status: **{s['status']}**",f"Execution mode: **{s.get('validation_mode','UNKNOWN')}**",f"Repository: `{s['repo']}`",'', '| Original task | Status | Reviews | Fallback |','|---|---|---:|---|']
        for tid in s['order']:
            t=s['tasks'][tid]; lines.append(f"| {tid} | {t['status']} | {t['round']}/5 | {t['fallback']} |")
        lines += ['', '## Evidence and coverage']
        for tid in s['order']:
            t=s['tasks'][tid]
            lines += [f'### {tid}', 'Requirements: '+json.dumps(t['spec']['requirements']), 'Acceptance: '+json.dumps(t['spec']['acceptance']),
                      'Implementation: '+json.dumps(t['implementation'],ensure_ascii=False), 'Review: '+json.dumps(t['review'],ensure_ascii=False),
                      f"[Checkpoint]({t['path']}/checkpoint.json) · [Findings]({t['path']}/findings.json)",
                      'Evidence: '+json.dumps(t['evidence'],ensure_ascii=False), '']
        lines += ['## Invocation measurements', json.dumps(s['invocations'],ensure_ascii=False,indent=2),
                  '## Session changes',json.dumps(s['sessions'],ensure_ascii=False,indent=2),
                  '## Task wall-clock seconds',json.dumps({k:(v.get('ended_at',time.time())-v['started_at']) if 'started_at' in v else None for k,v in s['tasks'].items()}),
                  '## Limits and measurements',json.dumps(s['metrics'],ensure_ascii=False,indent=2),
                  'Unavailable fields are null; cumulative billed tokens are never current context usage.',
                  'Baseline exceptions: '+json.dumps(s['config']['baseline_exceptions'],ensure_ascii=False),
                  'Pending questions: '+json.dumps(s['pending'],ensure_ascii=False),
                  'Detailed observable events, decisions, rebuttals and session changes: [discussion](discussion.md) · [decisions](decisions.md)',
                  'Completion requires every task and final gate VERIFIED. Local changes only; no push, merge or deploy.']
        atomic(self.path/'summary.md','\n'.join(lines).encode())
    @contextlib.contextmanager
    def transaction(self):
        with lock(self.path/'runner.lock'):
            self.load(); yield self
    def task(self,tid):
        require(tid in self.state['tasks'],'Unknown original task ID'); return self.state['tasks'][tid]
    def document_check(self):
        for d in self.state['manifest']['documents']:
            require(Path(d['path']).is_file() and digest(Path(d['path']).read_bytes())==d['sha256'],'Source specification changed; NEEDS_USER_INPUT: '+d['path'])
    def approve(self,answer):
        require(not self.state['approved'],'Run already approved')
        require(answer.strip(),'Record the actual user confirmation')
        self.state['approved']=True; self.state['status']='READY'
        self.decision(answer,self.state['order'],questions=['Initial plan, roles, gates, budgets, exceptions and session policy'])
        for t in self.state['tasks'].values(): t['status']='READY'
        self.commit('approved',{'decision_version':len(self.state['decisions'])})
    def decision(self,answer,scope,questions=None,category='plan'):
        self.state['decisions'].append({'version':len(self.state['decisions'])+1,'at':utc(),'answer':answer,'scope':scope,'questions':questions or [],'category':category})
    def bind(self,tid,execution,review,replace_reason=None):
        t=self.task(tid); require(execution and review and execution!=review,'Two real distinct management agent IDs required')
        if t['agents']: require(replace_reason,'Same task keeps managers unless checkpoint replacement is justified')
        for other in self.state['tasks'].values():
            if other is not t and other['agents']: require(not {execution,review}&set(other['agents'].values()),'Next task requires new managers')
        t.setdefault('started_at',time.time())
        old=t['agents']; t['agents']={'execution':execution,'review':review}; t['agent_history'].append({'agents':t['agents'],'reason':replace_reason or 'task start'})
        self.checkpoint(tid, 'manager binding/replacement')
        self.commit('agents_bound',{'task':tid,'agents':t['agents'],'previous':old,'reason':replace_reason})
    def checkpoint(self,tid,reason):
        t=self.task(tid)
        t['checkpoint']={'at':utc(),'reason':reason,'documents':self.state['manifest']['documents'], 'constraints':self.state['manifest'].get('constraints',[]),
                         'acceptance':t['spec']['acceptance'],'decisions':self.state['decisions'],'round':t['round'],
                         'snapshot':snapshot(self.state['repo']),'implementation':t['implementation'],'findings':t['findings'],
                         'evidence':t['evidence'],'failed_attempts':t['infra_failures'],'next_status':t['status'],
                         'reread':[d['path'] for d in self.state['manifest']['documents']], 'sessions':t['sessions']}
    def ensure(self,tid):
        s=self.state; t=self.task(tid)
        require(s['approved'],'Preflight confirmation required')
        require(s['status'] not in ('CANCELLED','FAILED'),'Run stopped')
        require(t['status'] not in ('WAITING_FOR_USER','BLOCKED','FAILED','CANCELLED','VERIFIED'),'Task is not runnable: '+t['status'])
        require(not s['pending'] or (s['config'].get('allow_independent_after_block') and all(tid not in q['affected'] for q in s['pending'])),'Waiting for user; affected work cannot run')
        for dep in t['spec'].get('dependencies',[]): require(self.task(dep)['status']=='VERIFIED','Dependency not verified: '+dep)
        for earlier in s['order'][:s['order'].index(tid)]:
            if self.task(earlier)['status']!='VERIFIED':
                require(s['config'].get('allow_independent_after_block') and self.task(earlier)['status'] in ('BLOCKED','WAITING_FOR_USER'),'Sequential task order is required')
        require(t['agents'],'Bind actual management subagents first')
        require(t['round']<5,'Review limit exhausted')
        self.document_check()
        return t
    def context(self,tid,info):
        t=self.task(tid)
        require(info.get('source') and isinstance(info.get('next_read_bytes'),int) and info['next_read_bytes']>=0,'Context needs source and next-read estimate')
        require(info.get('capacity') is None or (isinstance(info.get('used'),int) and 0<=info['used']<=info['capacity']),'Invalid reliable context metric')
        require(info.get('source')!='billed_tokens','Billed tokens are not current context')
        require(info.get('action') in ('resume','fresh','ask'),'Explicit context decision required')
        if info.get('capacity') is None and self.state['config']['context_policy']=='ask': require(info['action']=='ask','Unknown context policy requires asking')
        t['context']=dict(info,at=utc()); self.checkpoint(tid,'context assessment')
        self.commit('context',{'task':tid,'assessment':t['context']})
    def plan_call(self,tid,kind):
        t=self.ensure(tid)
        require(kind in ('implement','fix','review','reconcile'),'Unknown invocation kind')
        require(t['context'] and t['context']['action']!='ask','Context assessment or user clarification required before each call')
        s=self.state; limits=s['config']['limits']
        require(s['metrics']['calls']<limits['max_calls'] and s['metrics']['active_seconds']<limits['active_seconds'],'Total execution budget exhausted')
        role='reviewer' if kind in ('review','reconcile') else ('fallback' if t['fallback'] else 'primary')
        if kind in ('implement','fix'): require(t['round']<5,'No implementation after fifth review')
        if kind=='implement': require(t['implementation'] is None,'Initial implementation already completed; use fix')
        if kind=='fix': require(t['implementation'] is not None or tid=='_final','No initial implementation to fix')
        if kind in ('review','reconcile'):
            require(t['implementation'] is not None or tid=='_final','Implementation required before review')
            require(snapshot(s['repo'])['digest']==s['known_snapshot'],
                    'Unaccounted candidate snapshot change; inspect and restore or use approved recovery before review')
        if kind!='reconcile':
            require(t['independent'] is None,'Saved independent review requires reconciliation or explicit invalidate-review first')
        cfg=s['config']['roles'][role]; registry=[s['sessions'][x] for x in t['sessions'] if s['sessions'][x]['role']==role and x not in t.get('invalidated_review_sessions',[])]
        fresh=not registry or t['context']['action']=='fresh'
        reason='first invocation' if not registry else ('context policy' if fresh else 'same task continuation')
        if kind=='review' and t['round'] in (0,2): fresh=True; reason='round 1/3 independent review'
        if kind=='review' and t['spec']['high_risk'] and t['round']>=1 and t['review'] and not self.blocking(tid): fresh=True; reason='high-risk final candidate independent review'
        if kind=='reconcile':
            require(t['independent'],'Independent findings must be saved before reconciliation')
            require(t['independent']['snapshot']==snapshot(s['repo'])['digest'],'Candidate changed after independent review')
            registry=[s['sessions'][t['independent']['session_key']]]; fresh=False; reason='phase 2 reconciliation'
        session=None if fresh else registry[-1]
        if session:
            for k in ('provider','model','effort'): require(session[k]==cfg[k],'Session configuration drift')
            require(session['task']==tid and session['role']==role and session['repo']==s['repo'],'Session scope mismatch')
        return {'kind':kind,'role':role,'config':cfg,'fresh':fresh,'reason':reason,'session':session,'round':t['round']+1}
    def register_session(self,tid,plan,sid):
        require(isinstance(sid,str) and sid.strip(),'CLI omitted session ID')
        s=self.state; cfg=plan['config']; key=cfg['provider']+':'+sid
        if key in s['sessions']:
            old=s['sessions'][key]
            require(old['task']==tid and old['role']==plan['role'] and old['repo']==s['repo'],'Session cannot cross task/role/repository')
            require(plan.get('session',{}).get('session_id')==sid,'Resume returned an unexpected session ID')
            require(not plan['fresh'],'Fresh invocation reused a previous session')
        else:
            require(plan['fresh'],'Resume returned another session unexpectedly')
            s['sessions'][key]={'run_id':s['run_id'],'task':tid,'role':plan['role'],'provider':cfg['provider'],'model':cfg['model'],
                                'effort':cfg['effort'],'session_id':sid,'repo':s['repo'],'created_at':utc(),'reason':plan['reason']}
            self.task(tid)['sessions'].append(key)
        return key
    def blocking(self,tid): return [f for f in self.task(tid)['findings'].values() if f['blocking'] and f['state'] not in CLOSED]
    def pause(self,tid,questions):
        require(questions and all(question_valid(q) for q in questions),'Malformed clarification')
        t=self.task(tid); t['resume_status']=t['status']; t['status']='WAITING_FOR_USER'
        self.state['status']='WAITING_FOR_USER'; self.state.setdefault('wait_started',time.time())
        for q in questions:
            # Descendants are always affected; never trust an incomplete model list.
            affected={tid,*q['affected']}
            for other in self.state['order']:
                if affected&set(self.task(other)['spec'].get('dependencies',[])): affected.add(other)
            self.state['pending'].append(dict(q,affected=sorted(affected),task=tid))
        self.checkpoint(tid,'NEEDS_USER_INPUT'); self.commit('needs_user_input',{'task':tid,'questions':self.state['pending']})
    def answer(self,text,category='requirement'):
        require(self.state['pending'] and text.strip(),'No pending questions or empty user answer')
        qs=self.state['pending']; scope=sorted(set(x for q in qs for x in q['affected']))
        require(category in ('requirement','adjudication'),'Decision category must distinguish specification clarification from finding adjudication')
        self.decision(text,scope,qs,category)
        for tid in {q['task'] for q in qs}:
            t=self.task(tid); t['status']=t.pop('resume_status','READY'); self.checkpoint(tid,'user answer')
        self.state['metrics']['user_wait_seconds']+=max(0,time.time()-self.state.pop('wait_started',time.time()))
        self.state['pending']=[]; self.state['status']='READY'; self.commit('user_answer',{'version':len(self.state['decisions']),'scope':scope,'answer':text})
    def accept_implementation(self,tid,report,invocation):
        validate_report(report,'implement'); t=self.task(tid)
        if report['status']=='NEEDS_USER_INPUT': self.pause(tid,report['questions']); return
        ids=set()
        for x in report['responses']:
            require(x['id'] in t['findings'],'Response references unknown finding'); ids.add(x['id'])
            f=t['findings'][x['id']]; require(f['state'] not in CLOSED,'Cannot reopen a closed finding without reviewer evidence')
            f['state']='FIXED_PENDING_VERIFICATION' if x['action']=='ACCEPT' else 'REBUTTED_PENDING_ADJUDICATION'
            f.setdefault('history',[]).append({'actor':'implementer','response':x,'invocation':invocation})
        require({f['id'] for f in self.blocking(tid)}<=ids,'Every open blocking finding needs an explicit response')
        require(set(t['spec']['acceptance'])<=set(report['acceptance']),'Implementation omitted acceptance coverage')
        t['implementation']={'report':report,'snapshot':snapshot(self.state['repo'])['digest'],'invocation':invocation}
        t['review']=None; t['independent']=None; t['status']='REVIEWING'
        self.state['status']='REVIEWING'
        self.checkpoint(tid,'implementation complete'); self.commit('implementation',{'task':tid,**t['implementation']})
    def invalidate_review(self,tid,reason):
        t=self.task(tid); old=t['independent']
        require(not self.state['active'],'Cannot invalidate an active invocation')
        require(old is not None and reason.strip(),'Saved independent review and concrete invalidation reason required')
        for finding in old['report']['findings']:
            existing=t['findings'].get(finding['id'])
            if existing: require(all(existing[k]==finding[k] for k in ('file','requirement')),'Conflicting finding identity during invalidation')
        # A replacement session cannot make an independently found defect disappear.
        for finding in old['report']['findings']:
            existing=t['findings'].get(finding['id'])
            if existing:
                existing['blocking']=existing['blocking'] or finding['blocking']
                if existing['state'] in CLOSED: existing['state']='OPEN'
            else:
                t['findings'][finding['id']]={**finding,'state':'OPEN','history':[]}
        t.setdefault('invalidated_review_sessions',[]).append(old['session_key'])
        t['independent']=None; t['context']=None
        self.checkpoint(tid,'Independent review invalidated: '+reason)
        self.commit('independent_review_invalidated',{'task':tid,'reason':reason,'previous':old,
                    'snapshot':snapshot(self.state['repo'])['digest']})
    def gates_ok(self,tid,snap):
        t=self.task(tid); latest={e['gate']:e for e in t['evidence'] if e['phase']=='gate' and e['snapshot']==snap}
        return all(g['id'] in latest and (latest[g['id']]['exit_code']==0 or latest[g['id']].get('approved_baseline')) for g in t['spec']['gates'])
    def tdd_ok(self,tid):
        if tid=='_final': return True
        t=self.task(tid)
        if tid in self.state['config']['tdd_exceptions']: return True
        if t['implementation'] and t['implementation'].get('validated_tdd')=='test-after':
            return self.gates_ok(tid,snapshot(self.state['repo'])['digest'])
        greens=[e for e in t['evidence'] if e['phase']=='green' and e['exit_code']==0]
        reds=[e for e in t['evidence'] if e['phase']=='red' and e['exit_code']!=0 and e.get('red_expected')]
        return any(r['finished_at']<g['started_at'] and r['gate']==g['gate'] and r['snapshot']!=g['snapshot'] for r in reds for g in greens) or any(e['phase']=='test-after' and e['exit_code']==0 for e in t['evidence'])
    def record_review(self,tid,report,session_key,fresh,invocation,phase='complete'):
        validate_report(report,'review'); t=self.task(tid)
        if report['status']=='NEEDS_USER_INPUT': self.pause(tid,report['questions']); return
        snap=snapshot(self.state['repo'])['digest']; require(report['snapshot']==snap,'Stale review snapshot')
        require(t['round']<5,'Review limit exhausted')
        require(set(t['spec']['acceptance'])<=set(report['coverage']),'Review omitted acceptance criteria')
        if phase=='independent':
            require(fresh,'Independent stage must use fresh session')
            require(t['independent'] is None,'Saved independent review cannot be overwritten; reconcile or explicitly invalidate it')
            t['independent']={'report':copy.deepcopy(report),'snapshot':snap,'session_key':session_key,'invocation':invocation}
            atomic(self.path/t['path']/f"round-{t['round']+1:02d}"/'independent.json',encoded(t['independent']))
            self.commit('independent_findings_saved',{'task':tid,'round':t['round']+1,'evidence':t['path']+f"/round-{t['round']+1:02d}/independent.json"}); return
        if t['round'] in (0,2) or (t['spec']['high_risk'] and t['round']>=1 and not self.blocking(tid)):
            require(t['independent'] and t['independent']['snapshot']==snap,'Required fresh independent stage missing')
        for f in report['findings']:
            old=t['findings'].get(f['id'])
            if old: require(all(old[k]==f[k] for k in ('file','requirement')),'Stable finding ID reused for another defect')
            if old and old['blocking'] and not f['blocking']: raise Stop('Blocking finding needs evidence-based disposition, not silent downgrade')
            t['findings'][f['id']]={**f,'state':old['state'] if old and old['state'] not in CLOSED else 'OPEN','history':old.get('history',[]) if old else []}
        # Independent issues cannot disappear during reconciliation without an explicit disposition.
        if t['independent']:
            for f in t['independent']['report']['findings']:
                if f['id'] not in t['findings']: t['findings'][f['id']]={**f,'state':'OPEN','history':[]}
                else: require(not f['blocking'] or t['findings'][f['id']]['blocking'],'Independent finding cannot be silently downgraded')
        for update in report['finding_updates']:
            require(update.get('id') in t['findings'] and update.get('evidence'),'Unknown finding/update without evidence')
            f=t['findings'][update['id']]; target=update.get('state')
            allowed={'FIXED_PENDING_VERIFICATION':{'VERIFIED_FIXED','OPEN','BLOCKED'},
                     'REBUTTED_PENDING_ADJUDICATION':{'DISMISSED_WITH_EVIDENCE','OPEN','BLOCKED'},
                     'OPEN':{'OPEN','BLOCKED','DISMISSED_WITH_EVIDENCE'},'BLOCKED':{'OPEN','BLOCKED','DISMISSED_WITH_EVIDENCE'}}
            require(target in allowed.get(f['state'],set()),'Invalid reviewer ledger transition')
            f['state']=target; f['history'].append({'actor':'reviewer','update':update,'invocation':invocation})
        t['round']+=1
        if t['spec']['high_risk'] and t['round']>=2 and t['independent'] and t['independent']['snapshot']==snap:
            t['high_risk_snapshot']=snap
        t['review']={'report':report,'snapshot':snap,'round':t['round'],'invocation':invocation}
        passed=(not self.blocking(tid) and not report['unverified'] and self.gates_ok(tid,snap) and self.tdd_ok(tid)
                and (not t['spec']['high_risk'] or t['high_risk_snapshot']==snap))
        if passed:
            t['status']='VERIFIED'; t['ended_at']=time.time(); t['managers_checkpointed']=True; self.state['status']='VERIFIED' if all(x['status']=='VERIFIED' for x in self.state['tasks'].values()) else 'READY'
        elif t['round']==5: t['status']='BLOCKED'; t['ended_at']=time.time(); t['managers_checkpointed']=True; self.state['status']='BLOCKED'
        else:
            t['status']='FIXING'
            if t['round']>=2 and not passed: t['fallback']=True
        atomic(self.path/t['path']/f"round-{t['round']:02d}"/'review.json',encoded(t['review']))
        t['independent']=None
        self.state['known_snapshot']=snap
        self.checkpoint(tid,'review complete'); self.commit('review_complete',{'task':tid,'round':t['round'],'status':t['status'],
            'snapshot':snap,'report':report,'fallback':t['fallback'],'session_key':session_key})
    def audit(self):
        s=self.state; now=snapshot(s['repo'])['digest']
        if now==s.get('known_snapshot'): return []
        changed=[]
        for tid,t in s['tasks'].items():
            if t['status']=='VERIFIED': t['status']='BLOCKED'; changed.append(tid)
        s['status']='BLOCKED'
        self.commit('unaccounted_snapshot_change',{'tasks':changed,'snapshot':now,'expected':s.get('known_snapshot')})
        return changed
