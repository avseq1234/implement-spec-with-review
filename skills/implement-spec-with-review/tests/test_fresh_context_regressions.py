import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import test_engine
from core import Stop, snapshot
from test_primitives import review

class FreshContextRegressions(unittest.TestCase):
    setUp = test_engine.EngineTests.setUp

    def test_fixture_help_has_no_filesystem_side_effect(self):
        import make_fixture
        with patch.object(sys, 'argv', ['make_fixture.py', '--help']), patch('make_fixture.tempfile.mkdtemp', side_effect=AssertionError('help created a fixture')):
            with self.assertRaises(SystemExit) as result:
                make_fixture.main()
            self.assertEqual(result.exception.code, 0)

    def test_implementation_updates_overall_status(self):
        self.run.state['status'] = 'IMPLEMENTING'
        report = review(snapshot(self.repo)['digest'])
        report.update(status='IMPLEMENTED', responses=[], acceptance=['AC1'])
        self.run.accept_implementation('1.1', report, 'fixture-implement')
        self.assertEqual(self.run.state['status'], 'REVIEWING')

    def test_review_rejects_unaccounted_source_drift(self):
        self.run.context('1.1', {'source':'unknown', 'capacity':None, 'next_read_bytes':100, 'action':'fresh'})
        (self.repo / 'accidental-manager-context.json').write_text('{}')
        with self.assertRaisesRegex(Stop, 'snapshot'):
            self.run.plan_call('1.1', 'review')

    def test_saved_independent_cannot_be_overwritten(self):
        report = review(snapshot(self.repo)['digest'])
        self.run.record_review('1.1', report, 'codex:first', True, 'first', 'independent')
        with self.assertRaisesRegex(Stop, 'independent'):
            self.run.record_review('1.1', report, 'codex:second', True, 'second', 'independent')
        self.assertEqual(self.t['independent']['invocation'], 'first')

    def test_explicit_invalidation_keeps_findings_budgets_and_abandons_session(self):
        report = review(snapshot(self.repo)['digest'])
        report['findings'] = [test_engine.EngineTests.finding(self)]
        self.run.context('1.1', {'source':'unknown','capacity':None,'next_read_bytes':100,'action':'fresh'})
        plan = self.run.plan_call('1.1','review')
        key = self.run.register_session('1.1',plan,'old-review')
        self.run.record_review('1.1',report,key,True,'first','independent')
        self.run.state['metrics']['calls'] = 4
        self.run.invalidate_review('1.1','Session context damaged; original findings retained for reconciliation')
        self.run.load(); task = self.run.task('1.1')
        self.assertIsNone(task['independent'])
        self.assertIsNone(task['context'])
        self.assertEqual(task['findings']['F1']['state'],'OPEN')
        self.assertTrue(task['findings']['F1']['blocking'])
        self.assertEqual(task['round'],0)
        self.assertEqual(self.run.state['metrics']['calls'],4)
        self.assertEqual(self.run.state['history'][-1]['data']['previous']['invocation'],'first')
        self.run.context('1.1', {'source':'unknown','capacity':None,'next_read_bytes':100,'action':'resume'})
        self.assertTrue(self.run.plan_call('1.1','review')['fresh'])
        self.assertIsNone(self.run.plan_call('1.1','review')['session'])

    def test_pending_independent_blocks_cli_review_and_fix_plans(self):
        report = review(snapshot(self.repo)['digest'])
        self.run.record_review('1.1',report,'codex:first',True,'first','independent')
        self.run.context('1.1', {'source':'unknown','capacity':None,'next_read_bytes':100,'action':'fresh'})
        for kind in ('review','fix'):
            with self.subTest(kind=kind), self.assertRaisesRegex(Stop,'independent'):
                self.run.plan_call('1.1',kind)
