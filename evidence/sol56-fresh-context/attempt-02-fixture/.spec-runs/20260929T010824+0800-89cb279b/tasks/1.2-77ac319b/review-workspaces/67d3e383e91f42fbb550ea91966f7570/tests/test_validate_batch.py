import unittest
from unittest.mock import patch

import lib


class ValidateBatchTests(unittest.TestCase):
    def test_empty_list_returns_a_new_empty_list(self):
        values = []

        result = lib.validate_batch(values)

        self.assertEqual(result, [])
        self.assertIsNot(result, values)
        self.assertEqual(values, [])

    def test_valid_values_preserve_order_and_input(self):
        values = [3, 1, 2]
        original = values.copy()

        result = lib.validate_batch(values)

        self.assertEqual(result, [3, 1, 2])
        self.assertIsNot(result, values)
        self.assertEqual(values, original)

    def test_invalid_element_propagates_exact_exception_without_continuing(self):
        values = [2, -1, 4]
        original = values.copy()
        sentinel = ValueError("sentinel")
        validated = []

        def validate(value):
            validated.append(value)
            if value == -1:
                raise sentinel
            return value

        with patch("lib.validate_positive_integer", side_effect=validate):
            with self.assertRaises(ValueError) as raised:
                lib.validate_batch(values)

        self.assertIs(raised.exception, sentinel)
        self.assertEqual(validated, [2, -1])
        self.assertEqual(values, original)

    def test_real_scalar_errors_are_preserved(self):
        for values, exception_type, message in (
            ([1, True, 2], TypeError, "value must be a built-in int"),
            ([1, 0, 2], ValueError, "value must be greater than zero"),
        ):
            with self.subTest(values=values):
                original = values.copy()
                with self.assertRaisesRegex(exception_type, message):
                    lib.validate_batch(values)
                self.assertEqual(values, original)

    def test_non_builtin_list_inputs_raise_type_error(self):
        class ListSubclass(list):
            pass

        invalid_values = ((), "", None, {1: 2}, ListSubclass([1]))
        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(TypeError):
                    lib.validate_batch(values)


if __name__ == "__main__":
    unittest.main()
