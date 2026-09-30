import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from core import Stop
from adapters import build_argv, parse_output
from test_primitives import config, review

class AdapterTests(unittest.TestCase):
    def test_codex_noninteractive_safe_argv(self):
        a=build_argv(config()['roles']['primary'],'/tmp/repo','schema.json','out.json')
        self.assertIn('--no-daemon',a); self.assertIn('exec',a); self.assertIn('--json',a); self.assertIn('gpt-5.6-sol',a)
        self.assertNotIn('--dangerously-bypass-approvals-and-sandbox',a); self.assertEqual(a[-1],'-')
    def test_explicit_resume_never_last(self):
        a=build_argv(config()['roles']['primary'],'/tmp/repo','schema.json','out.json','known-id')
        self.assertIn('resume',a); self.assertIn('known-id',a); self.assertNotIn('--last',a)
    def test_claude_provider_effort_and_id(self):
        c=dict(config()['roles']['primary'],provider='claude',cli='claude',model='claude-sonnet-5',effort='high')
        a=build_argv(c,'/tmp/repo','schema.json','out.json','known-id')
        self.assertEqual(a[0],'claude'); self.assertIn('--resume',a); self.assertIn('--effort',a)
        self.assertNotIn('--dangerously-skip-permissions',a)
    def test_codex_complete_stream(self):
        r=review(); stream='\n'.join(json.dumps(x) for x in [{'type':'thread.started','thread_id':'sid'},
            {'type':'item.completed','item':{'type':'agent_message','text':json.dumps(r)}},
            {'type':'turn.completed','usage':{'input_tokens':10,'output_tokens':2}}])
        p=parse_output('codex',stream,json.dumps(r)); self.assertEqual(p['session_id'],'sid'); self.assertEqual(p['report'],r)
    def test_truncated_codex_rejected(self):
        with self.assertRaises(Stop): parse_output('codex','{"type":"thread.started","thread_id":"sid"}',json.dumps(review()))
    def test_claude_structured_result(self):
        r=review(); p=parse_output('claude',json.dumps({'type':'result','subtype':'success','is_error':False,'session_id':'s','structured_output':r}))
        self.assertEqual(p['session_id'],'s'); self.assertEqual(p['report'],r)
    def test_non_success_claude_rejected(self):
        with self.assertRaises(Stop): parse_output('claude',json.dumps({'type':'result','is_error':True,'session_id':'s','result':'no'}))
    def test_malformed_output_rejected(self):
        with self.assertRaises(Stop): parse_output('codex','garbage')
    def test_verified_model_default_omits_effort_flag(self):
        c=config()['roles']['primary']; c['effort']='model-default'
        a=build_argv(c,'/tmp/repo','schema.json','out.json')
        self.assertFalse(any('model_reasoning_effort' in x for x in a))
    def test_codex_image_is_explicit_attachment(self):
        c=config()['roles']['primary']; c['images']=['/tmp/diagram.png']
        a=build_argv(c,'/tmp/repo','schema.json','out.json')
        self.assertIn('--image',a); self.assertIn('/tmp/diagram.png',a)
    def test_prompt_injection_not_shell(self):
        c=config()['roles']['primary']; c['model']='$(touch /tmp/should-not-exist)'
        a=build_argv(c,'/tmp/repo','schema.json','out.json'); self.assertIn(c['model'],a)

if __name__=='__main__': unittest.main()
