import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import test_engine
from core import Stop, atomic, encoded, snapshot
from runner import recover, immutable_copy
from capture import capture

class RecoveryTests(test_engine.EngineTests):
    def test_capture_timeout_stops_descendant_writes(self):
        code="import subprocess,time,sys; subprocess.Popen([sys.executable,'-c',\"import time; from pathlib import Path; time.sleep(.4); Path('late-write.txt').write_text('bad')\"]); time.sleep(10)"
        r,_=capture(self.repo,self.repo/'.spec-runs/spool','gate','suite',[sys.executable,'-c',code],.1)
        self.assertTrue(r['timeout']); time.sleep(.5); self.assertFalse((self.repo/'late-write.txt').exists())
    def test_recover_checks_sidecar_before_handing_off(self):
        child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)'],start_new_session=True)
        try:
            stamp=subprocess.run(['ps','-p',str(child.pid),'-o','lstart='],capture_output=True,text=True,check=True).stdout.strip()
            self.run.state['active']={'id':'crash','task':'1.1','directory':'unknown','pid':None}; self.run.commit('crash-fixture',{})
            atomic(self.run.path/'active-process.json',encoded({'id':'crash','task':'1.1','directory':'unknown','pid':child.pid,'process_start':stamp}))
            with self.assertRaises(Stop): recover(self.run)
            self.assertIsNotNone(self.run.state['active'])
        finally: child.terminate(); child.wait(timeout=3)
    def test_isolation_preserves_tracked_ignored_and_deletion(self):
        (self.repo/'.gitignore').write_text('ignored.py\n'); (self.repo/'ignored.py').write_text('x=1')
        (self.repo/'deleted.py').write_text('gone')
        subprocess.run(['git','-C',str(self.repo),'add','-f','ignored.py','deleted.py'],check=True)
        (self.repo/'deleted.py').unlink(); snap=snapshot(self.repo)
        with tempfile.TemporaryDirectory() as tmp:
            target=immutable_copy(self.repo,Path(tmp)/'candidate',snap)
            copy=snapshot(target)
            self.assertEqual({k:v for k,v in snap['files'].items() if not v.get('deleted')},copy['files'])
            self.assertEqual(snap['files']['deleted.py'],{'deleted':True})

if __name__=='__main__': unittest.main()
