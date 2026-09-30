import unittest

from lib import validate_positive_integer


class ValidatePositiveIntegerTests(unittest.TestCase):
    def test_positive_builtin_int_is_returned_unchanged(self):
        value = 7

        self.assertIs(validate_positive_integer(value), value)

    def test_zero_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_positive_integer(0)

    def test_negative_int_raises_value_error(self):
        with self.assertRaises(ValueError):
            validate_positive_integer(-1)

    def test_non_builtin_int_values_raise_type_error(self):
        invalid_values = (True, 1.5, "1", None, object())

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    validate_positive_integer(value)


if __name__ == "__main__":
    unittest.main()
