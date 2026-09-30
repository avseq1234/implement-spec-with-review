import unittest

import lib


class ListSubclass(list):
    pass


class ValidateBatchTests(unittest.TestCase):
    def test_empty_list_returns_distinct_empty_list(self):
        values = []

        result = lib.validate_batch(values)

        self.assertEqual(result, [])
        self.assertIsNot(result, values)

    def test_validates_values_in_order_and_preserves_input(self):
        values = [3, 1, 2]
        original = values.copy()

        result = lib.validate_batch(values)

        self.assertEqual(result, [3, 1, 2])
        self.assertIsNot(result, values)
        self.assertEqual(values, original)

    def test_rejects_non_builtin_lists_with_type_error(self):
        invalid_values = ((), "", None, {1, 2}, ListSubclass([1, 2]))

        for values in invalid_values:
            with self.subTest(values=values):
                with self.assertRaises(TypeError):
                    lib.validate_batch(values)

    def test_propagates_first_invalid_element_error_without_mutation(self):
        cases = (([2, 0, "later"], ValueError), ([2, True], TypeError))

        for values, error_type in cases:
            with self.subTest(values=values):
                original = values.copy()

                with self.assertRaises(error_type):
                    lib.validate_batch(values)

                self.assertEqual(values, original)


if __name__ == "__main__":
    unittest.main()
