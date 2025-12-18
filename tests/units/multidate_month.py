import unittest
from datetime import date, time, timedelta
from multidate_v2 import MultiDateMonthday, EventTimestamp


class TestMultiDateMonthdayVulnerabilities(unittest.TestCase):

    def test_get_all_timestamps_february_31_infinite_loop(self):
        """Тест на потенциальную бесконечную петлю при обработке 31 февраля"""
        multidate = MultiDateMonthday([31], (12, 0))
        start_date = date(2023, 1, 31)
        end_date = date(2023, 4, 1)

        # Не должно вызывать бесконечный цикл
        results = list(multidate.get_all_timestamps(start_date, end_date))
        expected = [date(2023, 1, 31), date(2023, 3, 31)]
        self.assertEqual(results, expected)

    def test_get_all_timestamps_empty_monthdays(self):
        """Тест обработки пустого списка дней месяца"""
        multidate = MultiDateMonthday([], (12, 0))
        start_date = date(2023, 1, 1)
        end_date = date(2023, 1, 31)

        results = list(multidate.get_all_timestamps(start_date, end_date))
        self.assertEqual(results, [])

    def test_get_all_timestamps_single_day_corner_cases(self):
        """Тест крайних случаев для одного дня"""
        multidate = MultiDateMonthday([1], (12, 0))

        # Начальная дата - последний день месяца
        start_date = date(2023, 1, 31)
        end_date = date(2023, 3, 1)
        results = list(multidate.get_all_timestamps(start_date, end_date))
        expected = [date(2023, 2, 1), date(2023, 3, 1)]
        self.assertEqual(results, expected)

    def test_count_timestamps_leap_year_february(self):
        """Тест подсчета для високосного года и февраля"""
        multidate = MultiDateMonthday([29], (12, 0))

        # Високосный год
        start_date = date(2020, 2, 28)
        end_date = date(2020, 3, 1)
        count = multidate.count_timestamps(start_date, end_date)
        self.assertEqual(count, 1)  # 29 февраля 2020 существует

        # Невисокосный год
        start_date = date(2021, 2, 28)
        end_date = date(2021, 3, 1)
        count = multidate.count_timestamps(start_date, end_date)
        self.assertEqual(count, 0)  # 29 февраля 2021 не существует

    def test_count_timestamps_cross_year_boundary(self):
        """Тест подсчета при переходе через границу года"""
        multidate = MultiDateMonthday([31, 15], (12, 0))

        start_date = date(2023, 12, 15)
        end_date = date(2024, 1, 15)
        count = multidate.count_timestamps(start_date, end_date)

        # Должно быть: 15, 31 декабря 2023 и 15 января 2024
        self.assertEqual(count, 3)

    def test_count_timestamps_same_start_end_date(self):
        """Тест подсчета при одинаковых начальной и конечной датах"""
        multidate = MultiDateMonthday([15], (12, 0))

        # Дата совпадает с одним из дней месяца
        test_date = date(2023, 1, 15)
        count = multidate.count_timestamps(test_date, test_date)
        self.assertEqual(count, 1)

        # Дата не совпадает с днями месяца
        test_date = date(2023, 1, 10)
        count = multidate.count_timestamps(test_date, test_date)
        self.assertEqual(count, 0)

    def test_count_timestamps_versus_get_all_consistency(self):
        """Тест на согласованность count_timestamps и get_all_timestamps"""
        multidate = MultiDateMonthday([1, 15, 31], (12, 0))

        start_date = date(2023, 1, 1)
        end_date = date(2023, 12, 31)

        count_result = multidate.count_timestamps(start_date, end_date)
        all_results = list(multidate.get_all_timestamps(start_date, end_date))

        self.assertEqual(count_result, len(all_results))


if __name__ == '__main__':
    unittest.main()