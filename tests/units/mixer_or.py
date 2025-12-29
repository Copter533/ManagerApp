import unittest
from typing import Iterator, List, Union

from multidate_v2 import mix_gen_or


class TestMixDatesOr(unittest.TestCase):
    def test_both_empty(self):
        self.assertEqual(list(mix_gen_or([], [])), [])

    def test_first_empty(self):
        self.assertEqual(list(mix_gen_or([], [1, 2, 3])), [1, 2, 3])

    def test_second_empty(self):
        self.assertEqual(list(mix_gen_or([4, 5], [])), [4, 5])

    def test_no_common_elements(self):
        gen1 = [1, 3, 5]
        gen2 = [2, 4, 6]
        result = list(mix_gen_or(gen1, gen2))
        self.assertEqual(result, [1, 2, 3, 4, 5, 6])

    def test_with_common_elements(self):
        gen1 = [1, 2, 10]
        gen2 = [1, 3, 5]
        result = list(mix_gen_or(gen1, gen2))
        self.assertEqual(result, [1, 2, 3, 5, 10])

    def test_one_generator_ends_first(self):
        gen1 = [1, 3, 5, 7, 9]
        gen2 = [2, 4]
        result = list(mix_gen_or(gen1, gen2))
        self.assertEqual(result, [1, 2, 3, 4, 5, 7, 9])

    def test_second_longer(self):
        gen1 = [10, 20]
        gen2 = [5, 15, 25]
        result = list(mix_gen_or(gen1, gen2))
        self.assertEqual(result, [5, 10, 15, 20, 25])

    def test_with_generators(self):
        def gen_func1():
            yield from [1, 3, 5]
        def gen_func2():
            yield from [2, 4]
        result = list(mix_gen_or(gen_func1(), gen_func2()))
        self.assertEqual(result, [1, 2, 3, 4, 5])

    def test_all_common_elements(self):
        gen1 = [5, 10, 15]
        gen2 = [5, 10, 15]
        result = list(mix_gen_or(gen1, gen2))
        self.assertEqual(result, [5, 10, 15])

    def test_negative_numbers(self):
        gen1 = [-5, 0, 5]
        gen2 = [-3, 3]
        result = list(mix_gen_or(gen1, gen2))
        self.assertEqual(result, [-5, -3, 0, 3, 5])

if __name__ == '__main__':
    unittest.main()