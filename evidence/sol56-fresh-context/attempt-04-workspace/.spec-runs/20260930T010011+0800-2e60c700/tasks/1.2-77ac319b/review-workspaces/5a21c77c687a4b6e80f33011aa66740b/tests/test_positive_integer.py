import unittest

import lib


class ValidatePositiveIntegerTests(unittest.TestCase):
    def test_accepts_positive_builtin_integer_and_preserves_identity(self):
        value = 123456789012345678901234567890

        result = lib.validate_positive_integer(value)

        self.assertIs(result, value)

    def test_accepts_boundary_value_one(self):
        self.assertEqual(lib.validate_positive_integer(1), 1)

    def test_rejects_non_builtin_integers_with_type_error(self):
        invalid_values = (True, False, 1.0, "1", None, object(), [1])

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    lib.validate_positive_integer(value)

    def test_rejects_zero_and_negative_integers_with_value_error(self):
        for value in (0, -1, -12345678901234567890):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    lib.validate_positive_integer(value)
