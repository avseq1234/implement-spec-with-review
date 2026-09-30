import copy
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from core import Stop, snapshot, validate_config, resolve_roles, validate_report


def config():
    roles = {r: {'provider': 'codex', 'model': 'gpt-5.6-sol', 'display_name': 'Codex SOL 5.6', 'effort': e,
                 'verified_efforts': ['medium','high','xhigh'], 'capability_evidence': 'fixture capability probe',
                 'cli': 'codex'} for r,e in [('primary','medium'),('reviewer','high'),('fallback','xhigh')]}
    return {'roles': roles, 'limits': {'timeout_seconds': 600, 'retry_limit': 1, 'max_calls': 30,
            'active_seconds': 5400, 'heartbeat_seconds': 5}, 'context_policy': 'checkpoint-resume',
            'context_policy_confirmed': True, 'platform': 'posix', 'baseline_exceptions': [],
            'tdd_exceptions': [], 'allow_independent_after_block': False}


def review(snap='abc'):
    return {'status':'REVIEW_COMPLETE','snapshot':snap,'summary':'reviewed','findings':[],
            'coverage':['AC1'], 'unverified':[], 'scope_checked':['requirements','normal','boundary','error',
            'tests','callers','interfaces','cumulative_changes','security','data_integrity','concurrency',
            'performance','compatibility','scope'], 'questions':[], 'finding_updates':[]}

class PrimitiveTests(unittest.TestCase):
    def test_roles_are_independent(self):
        c=config(); self.assertEqual(validate_config(c), c)
        self.assertEqual([c['roles'][r]['effort'] for r in ['primary','reviewer','fallback']], ['medium','high','xhigh'])
    def test_provider_mismatch_is_rejected(self):
        c=config(); c['roles']['primary']['provider']='claude'
        with self.assertRaises(Stop): validate_config(c)
    def test_effort_no_silent_downgrade(self):
        c=config(); c['roles']['primary']['effort']='unknown'
        with self.assertRaises(Stop): validate_config(c)
    def test_required_budget(self):
        c=config(); del c['limits']['timeout_seconds']
        with self.assertRaises(Stop): validate_config(c)
    def test_supplied_roles_not_asked_again(self):
        c=config()['roles']; self.assertEqual(resolve_roles(c), {'roles':c,'missing':[]})
    def test_no_implicit_reuse(self):
        self.assertEqual(resolve_roles({}, config()['roles'])['missing'], ['primary','reviewer','fallback'])
    def test_explicit_reuse(self):
        c=config()['roles']; self.assertEqual(resolve_roles({}, c, True), {'roles':c,'missing':[]})
    def test_partial_role_settings_preserved(self):
        self.assertEqual(resolve_roles({'primary':{'model':'gpt-5.6-sol'}})['roles']['primary']['model'], 'gpt-5.6-sol')
    def test_valid_review(self): self.assertEqual(validate_report(review(), 'review'), review())
    def test_missing_review_scope_rejected(self):
        r=review(); r['scope_checked']=[]
        with self.assertRaises(Stop): validate_report(r,'review')
    def test_uncertainty_needs_evidence_and_options(self):
        r={'status':'NEEDS_USER_INPUT','questions':[{'question':'Which?'}]}
        with self.assertRaises(Stop): validate_report(r,'implement')
    def test_unproven_finding_not_confirmed(self):
        r=review(); r['findings']=[{'id':'F1','severity':'P1','blocking':True,'file':'a.py','line':1,
            'requirement':'AC1','trigger':'empty','impact':'crash','evidence':[],'direction':'reject'}]
        with self.assertRaises(Stop): validate_report(r,'review')
    def test_snapshots_include_untracked_and_dirty_but_exclude_runtime(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); subprocess.run(['git','init','-q',tmp],check=True)
            (p/'a.py').write_text('one'); a=snapshot(p)
            self.assertIsInstance(a, dict); self.assertIn('a.py',a['files'])
            (p/'a.py').write_text('two'); b=snapshot(p); self.assertNotEqual(a['digest'], b['digest'])
            (p/'.spec-runs/x').mkdir(parents=True); (p/'.spec-runs/x/state.json').write_text('{}')
            self.assertEqual(b['digest'],snapshot(p)['digest'])
            (p/'new.py').write_text('new'); self.assertNotEqual(b['digest'],snapshot(p)['digest'])
    def test_snapshot_captures_modes_and_symlinks(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp); subprocess.run(['git','init','-q',tmp],check=True)
            (p/'a').write_text('x'); a=snapshot(p); self.assertIsInstance(a,dict)
            os.chmod(p/'a',0o755); self.assertNotEqual(a['digest'],snapshot(p)['digest'])
            (p/'link').symlink_to('a'); self.assertIn('link',snapshot(p)['files'])

if __name__=='__main__': unittest.main()


class ProcessInspectionTests(unittest.TestCase):
    def test_rejects_nonzero_or_empty_identity(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from core import process_start, Stop
        for code, output in [(1, 'fake stamp'), (0, '  ')]:
            with self.subTest(code=code), patch('core.subprocess.run', return_value=SimpleNamespace(returncode=code,stdout=output)):
                with self.assertRaisesRegex(Stop, 'process inspection'):
                    process_start(123)

    def test_accepts_only_usable_identity(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from core import process_start
        with patch('core.subprocess.run', return_value=SimpleNamespace(returncode=0,stdout=' Mon Sep 28 17:01:00 2026\n')):
            self.assertEqual(process_start(123),'Mon Sep 28 17:01:00 2026')
