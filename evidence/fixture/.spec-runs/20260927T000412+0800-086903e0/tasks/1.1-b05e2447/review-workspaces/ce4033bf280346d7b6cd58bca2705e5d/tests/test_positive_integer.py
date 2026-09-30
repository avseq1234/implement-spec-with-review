import unittest

from lib import validate_positive_integer


class ValidatePositiveIntegerTests(unittest.TestCase):
    def test_accepts_positive_builtin_integers(self):
        self.assertEqual(validate_positive_integer(1), 1)
        self.assertEqual(validate_positive_integer(42), 42)

    def test_rejects_zero_and_negative_integers(self):
        for value in (0, -1, -42):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    validate_positive_integer(value)

    def test_rejects_bool_and_other_non_builtin_integer_types(self):
        for value in (True, False, 1.0, "1", None, object()):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    validate_positive_integer(value)


if __name__ == "__main__":
    unittest.main()
