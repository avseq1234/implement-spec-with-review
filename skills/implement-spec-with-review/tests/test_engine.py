import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from core import Run, Stop, snapshot
from test_primitives import config, review

class EngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup); self.repo=Path(self.tmp.name)
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        for n in ['high.md','tasks.md','spec.md']: (self.repo/n).write_text('fixture '+n)
        self.manifest={'documents':[{'path':n,'kind':k} for n,k in [('high.md','high-level'),('tasks.md','tasks'),('spec.md','spec')]],
            'tasks':[{'id':'1.1','requirements':['R1'],'acceptance':['AC1'],'dependencies':[],'high_risk':False,
                      'gates':[{'id':'suite','argv':[sys.executable,'-c','pass']}]}],
            'final_gates':[{'id':'suite','argv':[sys.executable,'-c','pass']}]}
        self.run=Run.create(self.repo,config(),self.manifest); self.run.approve('User confirmed fixture scope and all config')
        self.run.bind('1.1','exec-1','review-1'); self.t=self.run.task('1.1')
        self.t['implementation']={'snapshot':snapshot(self.repo)['digest'],'report':{},'invocation':'fixture'}
        self.t['evidence']=[{'phase':'test-after','exit_code':0,'gate':'suite','snapshot':snapshot(self.repo)['digest']},
                           {'phase':'gate','exit_code':0,'gate':'suite','snapshot':snapshot(self.repo)['digest']}]
    def r(self): return review(snapshot(self.repo)['digest'])
    def independent(self,report=None): self.run.record_review('1.1',report or self.r(),'codex:s',True,'i','independent')
    def complete(self,report=None): self.run.record_review('1.1',report or self.r(),'codex:s',False,'i')
    def finding(self): return {'id':'F1','severity':'P1','blocking':True,'file':'a.py','line':1,'requirement':'AC1','trigger':'empty','impact':'crash','evidence':['repro'],'direction':'reject'}
    def test_round1_stops_when_passed(self):
        self.independent(); self.complete(); self.assertEqual(self.t['status'],'VERIFIED'); self.assertEqual(self.t['round'],1)
        self.assertNotEqual(self.run.state['status'],'VERIFIED')
    def test_round3_fresh_and_fallback(self):
        r=self.r(); r['findings']=[self.finding()]; self.independent(r); self.complete(r); self.complete(r)
        self.run.context('1.1',{'source':'unavailable','capacity':None,'next_read_bytes':1,'action':'resume'})
        self.assertTrue(self.run.plan_call('1.1','review')['fresh']); self.assertEqual(self.run.plan_call('1.1','fix')['role'],'fallback')
    def test_five_round_cap_and_no_post_round5_fix(self):
        r=self.r(); r['findings']=[self.finding()]
        for n in range(5):
            if n in (0,2): self.independent(r)
            self.complete(r)
        self.assertEqual(self.t['status'],'BLOCKED')
        with self.assertRaises(Stop): self.run.plan_call('1.1','fix')
    def test_high_risk_needs_second_independent_and_survives_reload(self):
        self.t['spec']['high_risk']=True; self.independent(); self.complete()
        self.assertNotEqual(self.t['status'],'VERIFIED'); reload=Run(self.run.path)
        self.assertIsNone(reload.task('1.1')['independent'])
        with self.assertRaises(Stop): reload.record_review('1.1',self.r(),'codex:s',False,'i')
    def test_closed_regression_reopens(self):
        f=self.finding(); self.t['findings']['F1']={**f,'state':'VERIFIED_FIXED','history':[]}
        r=self.r(); r['findings']=[f]; self.independent(r); self.complete(r)
        self.assertNotEqual(self.t['status'],'VERIFIED'); self.assertEqual(self.t['findings']['F1']['state'],'OPEN')
    def test_independent_blocking_not_silently_downgraded(self):
        r=self.r(); r['findings']=[self.finding()]; self.independent(r)
        r['findings'][0]['blocking']=False
        with self.assertRaises(Stop): self.complete(r)
    def test_any_round2_gate_failure_triggers_fallback(self):
        r=self.r(); r['unverified']=['AC1 reproduction missing']; self.independent(r); self.complete(r); self.complete(r)
        self.assertTrue(self.t['fallback'])
    def test_resume_must_return_requested_session(self):
        cfg=config()['roles']['primary']; p={'role':'primary','config':cfg,'fresh':True,'reason':'first'}
        self.run.register_session('1.1',p,'old'); self.run.register_session('1.1',p,'new')
        p['fresh']=False; p['session']=self.run.state['sessions']['codex:new']
        with self.assertRaises(Stop): self.run.register_session('1.1',p,'old')
    def test_session_cannot_cross_roles(self):
        cfg=config()['roles']['primary']; p={'role':'primary','config':cfg,'fresh':True,'reason':'first'}
        self.run.register_session('1.1',p,'sid'); p['role']='reviewer'
        with self.assertRaises(Stop): self.run.register_session('1.1',p,'sid')
    def test_wait_answer_preserves_round_and_decisions(self):
        self.t['round']=2; self.run.pause('1.1',[{'question':'which','evidence':['conflict'],'options':['A: impact','B: impact'],'affected':['1.1']}])
        with self.assertRaises(Stop): self.run.ensure('1.1')
        self.run.answer('User chooses A'); r=Run(self.run.path)
        self.assertEqual(r.task('1.1')['round'],2); self.assertEqual(r.state['decisions'][-1]['answer'],'User chooses A')
        self.assertIn('User chooses A',(r.path/'decisions.md').read_text()); self.assertIn('User chooses A',(r.path/'discussion.md').read_text())
    def test_manager_replacement_preserves_round(self):
        self.t['round']=2; self.run.bind('1.1','exec-new','review-new','checkpoint context exhausted')
        self.assertEqual(self.t['round'],2); self.assertEqual(len(self.t['agent_history']),2)
    def test_stale_review_refused(self):
        r=self.r(); (self.repo/'new.py').write_text('new')
        with self.assertRaises(Stop): self.independent(r)
    def test_unverified_final_prevents_overall_success(self):
        self.independent(); self.complete(); self.assertEqual(self.t['status'],'VERIFIED')
        self.assertNotEqual(self.run.state['status'],'VERIFIED')
    def test_baseline_not_silent(self):
        self.t['evidence'][-1]['exit_code']=1; self.independent(); self.complete(); self.assertNotEqual(self.t['status'],'VERIFIED')
    def test_original_id_and_safe_path_mapping(self):
        self.assertEqual(self.t['spec']['id'],'1.1'); self.assertTrue((self.run.path/self.t['path']/'checkpoint.json').exists())
    def test_implementer_cannot_close_findings(self):
        self.t['findings']['F1']={**self.finding(),'state':'OPEN','history':[]}
        r={'status':'IMPLEMENTED','summary':'fixed','questions':[],'responses':[{'id':'F1','action':'ACCEPT','evidence':['a.py']}],'acceptance':['AC1']}
        self.run.accept_implementation('1.1',r,'i'); self.assertEqual(self.t['findings']['F1']['state'],'FIXED_PENDING_VERIFICATION')
    def test_rebuttal_needs_reviewer_disposition(self):
        self.t['findings']['F1']={**self.finding(),'state':'OPEN','history':[]}
        r={'status':'IMPLEMENTED','summary':'rebut','questions':[],'responses':[{'id':'F1','action':'REBUT','evidence':['spec']}],'acceptance':['AC1']}
        self.run.accept_implementation('1.1',r,'i'); self.assertTrue(self.run.blocking('1.1'))
        rr=self.r(); rr['finding_updates']=[{'id':'F1','state':'DISMISSED_WITH_EVIDENCE','evidence':['spec confirmed']}]
        self.independent(rr); self.complete(rr); self.assertEqual(self.t['findings']['F1']['state'],'DISMISSED_WITH_EVIDENCE')

if __name__=='__main__': unittest.main()
