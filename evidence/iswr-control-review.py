import sys,tempfile,subprocess,copy,json
from pathlib import Path
sys.path[:0]=['/Users/weihongda/projects/choreshandling/tools/implement-spec-with-review/scripts','/Users/weihongda/projects/choreshandling/tools/implement-spec-with-review/tests']
from core import Run,snapshot
from test_primitives import config,review

def fixture(high=False):
 p=Path(tempfile.mkdtemp(prefix='iswr-review-')); subprocess.run(['git','init','-q',str(p)],check=True)
 for n in ('high','tasks','spec'): (p/n).write_text(n)
 c=config(); c['tdd_exceptions']=['1']
 m={'documents':[{'kind':k,'path':n} for k,n in [('high-level','high'),('tasks','tasks'),('spec','spec')]],'tasks':[{'id':'1','requirements':['R1'],'acceptance':['AC1'],'dependencies':[],'high_risk':high,'gates':[{'id':'tests','argv':['true']}]}],'final_gates':[{'id':'all','argv':['true']}]}
 r=Run.create(p,c,m); r.approve('approved fixture'); r.bind('1','exec','review'); return p,r

def passing_evidence(r):
 s=snapshot(r.state['repo'])['digest']; r.task('1')['evidence']=[{'phase':'gate','gate':'tests','snapshot':s,'exit_code':0}]; return s

def finding(): return {'id':'F1','severity':'P1','blocking':True,'file':'x.py','line':1,'requirement':'AC1','trigger':'empty','impact':'crash','evidence':['reproduced'],'direction':'fix'}

# The first independent stage must not be reused as the required extra independent review.
p,r=fixture(True); s=passing_evidence(r); rep=review(s)
r.record_review('1',rep,'codex:first',True,'i1',phase='independent'); r.record_review('1',rep,'codex:first',False,'i2')
print('INDEPENDENT_AFTER_COMMIT_MEMORY',r.task('1')['independent'])
r=Run(r.path); print('INDEPENDENT_AFTER_RELOAD_PRESENT',r.task('1')['independent'] is not None)
r.record_review('1',rep,'codex:first',False,'i3')
print('HIGH_RISK_WITH_ONLY_ONE_INDEPENDENT_STAGE',r.task('1')['status'],r.task('1')['round'])

# Recurring finding from a previous verified fix stays closed despite evidence.
p,r=fixture(); s=passing_evidence(r); t=r.task('1'); t['round']=1; t['findings']['F1']={**finding(),'state':'VERIFIED_FIXED','history':[]}
rep=review(s); rep['findings']=[finding()]; r.record_review('1',rep,'codex:review',False,'i4')
print('REGRESSION',r.task('1')['status'],r.task('1')['findings']['F1']['state'])

# Gate failure includes incomplete verification, not only failing commands.
p,r=fixture(); s=passing_evidence(r); t=r.task('1'); t['round']=1
rep=review(s); rep['unverified']=['acceptance behavior not yet verified']; r.record_review('1',rep,'codex:review',False,'i5')
print('ROUND2_INCOMPLETE_GATE_FALLBACK',t['status'],t['fallback'])

# Existing session ID returned by resume must equal the requested explicit ID.
p,r=fixture(); cfg=r.state['config']['roles']['primary']; plan={'config':cfg,'role':'primary','fresh':True,'reason':'test'}
r.register_session('1',plan,'old'); r.register_session('1',plan,'new'); plan.update(fresh=False,session=r.state['sessions']['codex:new'])
print('MISMATCHED_RESUME_ACCEPTED',r.register_session('1',plan,'old'))

# Independent blocking evidence must not vanish through an unexplained downgrade.
p,r=fixture(); s=passing_evidence(r); rep=review(s); rep['findings']=[finding()]
r.record_review('1',rep,'codex:fresh',True,'i6',phase='independent')
rep=copy.deepcopy(rep); rep['findings'][0]['blocking']=False
r.record_review('1',rep,'codex:fresh',False,'i7')
print('INDEPENDENT_BLOCKING_DOWNGRADE',r.task('1')['status'],r.task('1')['findings']['F1']['blocking'])
