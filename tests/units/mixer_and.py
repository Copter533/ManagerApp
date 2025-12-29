import unittest
from typing import Iterator, List

from multidate_v2 import mix_gen_and


class TestMixDatesAnd(unittest.TestCase):
    def test_both_empty(self):
        """Оба генератора пусты"""
        result = list(mix_gen_and([], []))
        self.assertEqual(result, [])

    def test_first_empty(self):
        """Первый генератор пуст"""
        result = list(mix_gen_and([], [1, 2, 3]))
        self.assertEqual(result, [])

    def test_second_empty(self):
        """Второй генератор пуст"""
        result = list(mix_gen_and([4, 5, 6], []))
        self.assertEqual(result, [])

    def test_no_common_elements(self):
        """Нет общих элементов"""
        gen1 = [1, 3, 5]
        gen2 = [2, 4, 6]
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, [])

    def test_single_common_element(self):
        """Один общий элемент"""
        gen1 = [1, 2, 3]
        gen2 = [2, 4, 5]
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, [2])

    def test_multiple_common_elements(self):
        """Несколько общих элементов"""
        gen1 = [1, 3, 5, 7, 9]
        gen2 = [2, 3, 5, 8, 9]
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, [3, 5, 9])

    def test_all_common(self):
        """Все элементы общие"""
        gen1 = [10, 20, 30]
        gen2 = [10, 20, 30]
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, [10, 20, 30])

    def test_different_lengths(self):
        """Генераторы разной длины"""
        gen1 = [1, 2, 3, 4, 5]
        gen2 = [3, 4, 5, 6, 7, 8, 9]
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, [3, 4, 5])

    def test_with_generators(self):
        """Тест с настоящими генераторами"""

        def gen1():
            yield from [5, 10, 15, 20]

        def gen2():
            yield from [10, 20, 30]

        result = list(mix_gen_and(gen1(), gen2()))
        self.assertEqual(result, [10, 20])

    def test_duplicates_in_one(self):
        """Дубликаты в одном генераторе"""
        gen1 = [1, 1, 2, 3]
        gen2 = [1, 2, 2, 4]
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, [1, 2])

    def test_large_sequences(self):
        """Большие последовательности"""
        gen1 = list(range(0, 1000, 2))  # Четные
        gen2 = list(range(1, 1000, 2))  # Нечетные
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, [])

        gen1 = list(range(1000))
        gen2 = list(range(500, 1500))
        result = list(mix_gen_and(gen1, gen2))
        self.assertEqual(result, list(range(500, 1000)))


if __name__ == '__main__':
    unittest.main()