#!/usr/bin/env python3
"""Independent acceptance checks derived from raw fixture specs; never shown to test agent."""
import contextlib
import importlib.util
import io
from pathlib import Path
import sys
import unittest
repo=Path(sys.argv.pop(1)).resolve()
spec=importlib.util.spec_from_file_location('observed_candidate',repo/'lib.py')
lib=importlib.util.module_from_spec(spec); spec.loader.exec_module(lib)
class IntSubclass(int): pass
class ListSubclass(list): pass
class Acceptance(unittest.TestCase):
    def test_positive_builtin_ints(self):
        for value in (1,2,257,10**100):
            with self.subTest(value=value): self.assertEqual(lib.validate_positive_integer(value),value)
    def test_nonpositive_values(self):
        for value in (0,-1,-10**100):
            with self.subTest(value=value),self.assertRaises(ValueError): lib.validate_positive_integer(value)
    def test_exact_int_type(self):
        for value in (True,False,1.0,'1',None,[],{},IntSubclass(1),object()):
            with self.subTest(type=type(value).__name__),self.assertRaises(TypeError): lib.validate_positive_integer(value)
    def test_batch_order_copy_empty(self):
        for values in ([],[1],[3,1,3,10**100]):
            before=values.copy(); result=lib.validate_batch(values)
            self.assertEqual(result,before); self.assertIsNot(result,values); self.assertEqual(values,before)
    def test_exact_list_type(self):
        for values in ((),None,'1',1,{1},ListSubclass([1])):
            with self.subTest(type=type(values).__name__),self.assertRaises(TypeError): lib.validate_batch(values)
    def test_first_error_and_preservation(self):
        for values,error in (([0,'bad'],ValueError),(['bad',0],TypeError),([1,False,0],TypeError),([2,-1,True],ValueError)):
            before=values.copy()
            with self.assertRaises(error): lib.validate_batch(values)
            self.assertEqual(values,before)
    def test_no_console_side_effects(self):
        out=io.StringIO(); err=io.StringIO()
        with contextlib.redirect_stdout(out),contextlib.redirect_stderr(err):
            lib.validate_positive_integer(1); lib.validate_batch([1,2])
            for fn,arg in ((lib.validate_positive_integer,0),(lib.validate_batch,[False])):
                try: fn(arg)
                except (ValueError,TypeError): pass
        self.assertEqual(out.getvalue(),''); self.assertEqual(err.getvalue(),'')
if __name__=='__main__': unittest.main(verbosity=2)
