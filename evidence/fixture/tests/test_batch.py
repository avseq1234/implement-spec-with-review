import unittest

from lib import validate_batch


class ValidateBatchTests(unittest.TestCase):
    def test_empty_list_returns_distinct_empty_list(self):
        values = []

        result = validate_batch(values)

        self.assertEqual(result, [])
        self.assertIsNot(result, values)

    def test_valid_list_returns_values_in_order_without_modifying_input(self):
        values = [3, 1, 2]
        original = values.copy()

        result = validate_batch(values)

        self.assertEqual(result, [3, 1, 2])
        self.assertIsNot(result, values)
        self.assertEqual(values, original)

    def test_rejects_non_builtin_list_inputs(self):
        class ListSubclass(list):
            pass

        for values in ((1, 2), "12", None, ListSubclass([1, 2])):
            with self.subTest(values=values):
                with self.assertRaises(TypeError):
                    validate_batch(values)

    def test_invalid_elements_use_scalar_contract_and_preserve_input(self):
        cases = (([1, True, 2], TypeError), ([1, 0, True], ValueError))
        for values, exception_type in cases:
            with self.subTest(values=values):
                original = values.copy()
                with self.assertRaises(exception_type):
                    validate_batch(values)
                self.assertEqual(values, original)


if __name__ == "__main__":
    unittest.main()
