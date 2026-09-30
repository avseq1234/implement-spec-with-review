import unittest
import lib
class Baseline(unittest.TestCase):
    def test_interfaces_exist(self):
        self.assertTrue(callable(lib.validate_positive_integer))
        self.assertTrue(callable(lib.validate_batch))
