import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from core import Run, Stop, lock, snapshot
from runner import invoke, gates, recover, process, prompt_for
import test_engine

class RuntimeTests(test_engine.EngineTests):
    def setUp(self):
        super().setUp()
        fake=Path(__file__).parent/'fake_cli.py'
        for r in self.run.state['config']['roles'].values():
            r.update(provider='fake',cli=sys.executable,prefix_args=[str(fake)],capability_evidence='fake only')
        self.run.commit('fixture_adapter',{})
    def assess(self,action='resume'):
        self.run.context('1.1',{'source':'unavailable','capacity':None,'next_read_bytes':100,'action':action})
    def test_missing_process_inspection_stops_before_provider_and_budget(self):
        self.assess()
        calls=self.run.state['metrics']['calls']
        actual_run=subprocess.run
        def denied(argv, *args, **kwargs):
            if argv[0]=='ps': raise PermissionError('process inspection denied')
            return actual_run(argv,*args,**kwargs)
        with patch('runner.subprocess.run',side_effect=denied), patch('runner.process',side_effect=AssertionError('provider launched before environment check')) as provider:
            with self.assertRaisesRegex(Stop,'process inspection'):
                invoke(self.run,'1.1','review')
            provider.assert_not_called()
        self.run.load()
        self.assertEqual(self.run.state['metrics']['calls'],calls)
        self.assertIsNone(self.run.state['active'])
        self.assertEqual(self.run.task('1.1')['infra_failures'],{})

    def test_prompt_preserves_existing_spec_inputs_directory(self):
        original=self.repo/'_spec_inputs'; original.mkdir(); (original/'user.txt').write_text('keep me')
        t=self.run.task('1.1'); t['implementation']=None; self.assess()
        plan=self.run.plan_call('1.1','implement')
        prompt_for(self.run,'1.1',plan,self.repo,snapshot(self.repo),self.repo/'context.json')
        self.assertTrue((original/'user.txt').exists())
        self.assertEqual((original/'user.txt').read_text(),'keep me')
    def test_fake_fresh_then_reconcile_complete(self):
        self.assess(); result=invoke(self.run,'1.1','review'); self.assertEqual(result['next'],'reconcile')
        self.assess(); result=invoke(self.run,'1.1','reconcile'); self.assertEqual(result['status'],'VERIFIED')
        self.assertEqual(result['round'],1)
    def test_fake_malformed_does_not_consume_round(self):
        self.run.state['config']['roles']['reviewer']['prefix_args']+=['--scenario','malformed']; self.run.commit('fixture_case',{})
        self.assess()
        with self.assertRaises(Stop): invoke(self.run,'1.1','review')
        self.assertEqual(self.run.task('1.1')['round'],0)
    def test_fake_nonzero_does_not_pass(self):
        self.run.state['config']['roles']['reviewer']['prefix_args']+=['--scenario','nonzero']; self.run.commit('fixture_case',{})
        self.assess()
        with self.assertRaises(Stop): invoke(self.run,'1.1','review')
        self.assertNotEqual(self.run.task('1.1')['status'],'VERIFIED')
    def test_fake_question_blocks_then_answer_resumes(self):
        self.run.state['config']['roles']['reviewer']['prefix_args']+=['--scenario','question']; self.run.commit('fixture_case',{})
        self.assess(); result=invoke(self.run,'1.1','review'); self.assertEqual(result['status'],'WAITING_FOR_USER')
        self.run.answer('A'); self.run.load(); self.assertEqual(self.run.task('1.1')['round'],0)
    def test_timeout_kills_process_and_no_review_credit(self):
        self.run.state['config']['limits']['timeout_seconds']=.15
        self.run.state['config']['roles']['reviewer']['prefix_args']+=['--scenario','timeout']; self.run.commit('fixture_case',{})
        self.assess()
        with self.assertRaises(Stop): invoke(self.run,'1.1','review')
        self.assertEqual(self.run.task('1.1')['round'],0); self.assertIsNone(self.run.state['active'])
    def test_one_writer_across_runs(self):
        with lock(Path(self.run.state['common_git_dir'])/'spec-run-writer.lock'):
            self.assess()
            with self.assertRaises(Stop): invoke(self.run,'1.1','review')
    def test_recover_does_not_rerun_unknown_write(self):
        self.run.state['active']={'pid':None,'task':'1.1','directory':'unknown','id':'interrupted'}; self.run.commit('interrupted',{})
        result=recover(self.run); self.assertFalse(result['rerun']); self.assertEqual(result['status'],'WAITING_FOR_USER')
    def test_external_edit_invalidates_verified(self):
        self.independent(); self.complete(); (self.repo/'new.py').write_text('new')
        result=recover(self.run); self.assertEqual(result['status'],'BLOCKED'); self.assertIn('1.1',result['invalidated'])
    def test_gates_have_actual_evidence(self):
        ev=gates(self.run,'1.1'); self.assertEqual(ev[0]['exit_code'],0); self.assertTrue((self.run.path/ev[0]['path']).exists())
    def test_missing_test_first_proof_is_disclosed_without_pausing(self):
        self.run.task('1.1')['evidence']=[]
        self.run.task('1.1')['implementation']['report']={'summary':'implementation existed before evidence','tdd':'test-first'}
        self.run.commit('fixture_missing_red',{})
        gates(self.run,'1.1')
        t=self.run.task('1.1')
        self.assertEqual(t['implementation'].get('validated_tdd'),'test-after')
        self.assertTrue(self.run.tdd_ok('1.1'))
        self.assertNotEqual(t['status'],'WAITING_FOR_USER')
        self.assertIn('test-after',(self.run.path/'discussion.md').read_text())
    def test_log_changes_do_not_invalidate(self):
        self.independent(); self.complete(); self.run.commit('log-only',{'details':'x'})
        self.assertEqual(recover(self.run)['invalidated'],[])

if __name__=='__main__': unittest.main()
