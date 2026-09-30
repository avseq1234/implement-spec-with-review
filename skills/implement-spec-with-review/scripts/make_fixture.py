#!/usr/bin/env python3
"""Create the user-approved isolated, local-only validation repository."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
ROOT=Path(__file__).resolve().parents[1]

def main():
    import argparse
    argparse.ArgumentParser(description=__doc__).parse_args()
    repo=Path(tempfile.mkdtemp(prefix='implement-spec-smoke-',dir='/private/tmp'))
    files={
      '.gitignore':'__pycache__/\n*.pyc\n',
      'lib.py':'def validate_positive_integer(value):\n    return None\n\ndef validate_batch(values):\n    return None\n',
      'tests/test_baseline.py':'import unittest\nimport lib\nclass Baseline(unittest.TestCase):\n    def test_interfaces_exist(self):\n        self.assertTrue(callable(lib.validate_positive_integer))\n        self.assertTrue(callable(lib.validate_batch))\n',
      'high-level.md':'# Fixture design\nProvide a pure, side-effect-free Python validation library. No third-party dependencies. Preserve caller input. Task 1.1 implements a scalar contract; task 1.2 composes it for batches. No network, logging, persistence, CLI application, or other features.\n',
      'openspec/tasks.md':'# Tasks\n- [ ] 1.1 Implement and test validate_positive_integer.\n- [ ] 1.2 Implement and test validate_batch, depending on 1.1.\n',
      'openspec/proposal.md':'# Proposal\nValidate scalar and batch input consistently with observable exceptions. Deliver only local Python implementation and tests.\n',
      'openspec/design.md':'# Design\nUse validate_positive_integer from validate_batch; no mutation or partial output. Exceptions propagate. Existing placeholder bodies return None and must be implemented with TDD.\n',
      'openspec/spec.md':'# Requirements and scenarios\nR1 / AC1: validate_positive_integer(value) accepts built-in int (type(value) is int) greater than zero and returns the same value. bool, floats, strings, None and other types raise TypeError. Zero and negative ints raise ValueError. Test normal, boundary and error paths.\nR2 / AC2: validate_batch(values) accepts a built-in list only, else TypeError. It returns a NEW list of validated integers in input order, without modifying input. Empty list returns a new empty list. Every element uses the exact R1 contract. First invalid element raises the same TypeError or ValueError; no partial result is returned. Test empty, valid, invalid element, input type and input preservation.\n'}
    for n,txt in files.items(): p=repo/n; p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt)
    subprocess.run(['git','init','-q',str(repo)],check=True)
    subprocess.run(['git','-C',str(repo),'add','.'],check=True)
    subprocess.run(['git','-C',str(repo),'-c','user.name=Skill Fixture','-c','user.email=fixture@example.invalid','commit','-qm','Isolated fixture baseline'],check=True)
    roles={r:{'display_name':'Codex SOL 5.6','provider':'codex','cli':'codex','model':'gpt-5.6-sol','effort':e,
              'verified_efforts':['low','medium','high','xhigh','max','ultra'],
              'capability_evidence':'codex-cli 0.158.0-alpha.2.1 help + local models_cache.json; real access pending smoke'}
           for r,e in [('primary','medium'),('reviewer','high'),('fallback','xhigh')]}
    config={'roles':roles,'limits':{'timeout_seconds':600,'retry_limit':1,'max_calls':30,'active_seconds':5400,'heartbeat_seconds':5},
            'context_policy':'checkpoint-resume','context_policy_confirmed':True,'baseline_exceptions':[],'tdd_exceptions':[],
            'allow_independent_after_block':False,'platform':'posix'}
    gate={'id':'suite','argv':[sys.executable,'-m','unittest','discover','-s','tests','-v']}
    manifest={'documents':[{'path':n,'kind':k} for n,k in [('high-level.md','high-level'),('openspec/tasks.md','tasks'),('openspec/spec.md','spec'),('openspec/design.md','design'),('openspec/proposal.md','proposal')]],
              'constraints':['pure functions','no third-party dependencies','no scope expansion','preserve input and original files'],
              'tasks':[{'id':'1.1','requirements':['R1'],'acceptance':['AC1'],'dependencies':[],'high_risk':False,'gates':[gate]},
                       {'id':'1.2','requirements':['R2'],'acceptance':['AC2'],'dependencies':['1.1'],'high_risk':False,'gates':[gate]}],
              'final_gates':[gate]}
    # Preflight inputs outside repo; do not contaminate candidate snapshots.
    prep=repo.parent/(repo.name+'-preflight'); prep.mkdir()
    (prep/'config.json').write_text(json.dumps(config,indent=2)); (prep/'manifest.json').write_text(json.dumps(manifest,indent=2))
    (prep/'approval.txt').write_text('User confirmed fixture validation, Codex primary medium / reviewer high / fallback xhigh, budgets 600 seconds per call, 30 calls, 5400 active seconds, retry 1, context checkpoint-resume, no baseline exceptions. Keep original code; test-after must be disclosed and verified without pausing solely for that deviation. Documentation uses structural and independent scenario validation. Claude remains untested. Controlled fallback session-switch smoke is authorized; no fabricated production finding.\n')
    print(json.dumps({'repo':str(repo),'preflight':str(prep)}))
if __name__=='__main__': main()
