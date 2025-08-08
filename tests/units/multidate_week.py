import unittest
from datetime import date

from multidate_v2 import MultiDateWeekday, EventTimestamp


class TestWeekdays(unittest.TestCase):
    def test_simple(self):
        """Тест простой - ровно неделя"""
        weekends = MultiDateWeekday(
            weekdays=[6, 7],  # Сб Вс
            time=[0, 0]
        )
        self.assertEqual(
            list(weekends.get_all_timestamps(date(2025, 7, 7), date(2025, 7, 13))),
            [
                EventTimestamp(date(2025, 7, 12), 0, 0),
                EventTimestamp(date(2025, 7, 13), 0, 0),
            ]
        )

    def test_month(self):
        """Тест месяца - считаем количество сред"""
        weekends = MultiDateWeekday(
            weekdays=[3],  # Ср
            time=[0, 0]
        )
        self.assertEqual(
            len(tuple(weekends.get_all_timestamps(date(2025, 7, 1), date(2025, 7, 31)))),
            5
        )

    def test_first_bad_next_good(self):
        """Первый день недели отпадает, второй подходит"""
        weekends = MultiDateWeekday(
            weekdays=[3, 7],  # Ср Вс
            time=[0, 0]
        )
        self.assertEqual(
            list(weekends.get_all_timestamps(date(2025, 7, 11), date(2025, 7, 15))),
            [
                EventTimestamp(date(2025, 7, 13), 0, 0)
            ]
        )

    def test_single_day_in_range(self):
        """Тест одного дня в середине диапазона"""
        wednesday = MultiDateWeekday(weekdays=[3], time=[900, 1700])
        result = list(wednesday.get_all_timestamps(date(2025, 7, 9), date(2025, 7, 9)))
        self.assertEqual(
            result,
            [EventTimestamp(date(2025, 7, 9), 900, 1700)]
        )

    def test_no_days_in_range(self):
        """Тест отсутствия дней недели в диапазоне"""
        fridays = MultiDateWeekday(weekdays=[5], time=[0, 0])
        result = list(fridays.get_all_timestamps(date(2025, 7, 7), date(2025, 7, 10)))
        self.assertEqual(len(result), 0)

    def test_cross_month_boundary(self):
        """Тест перехода между месяцами"""
        mondays = MultiDateWeekday(weekdays=[1], time=[800, 2000])
        result = list(mondays.get_all_timestamps(date(2025, 6, 30), date(2025, 7, 7)))
        self.assertEqual(
            result,
            [
                EventTimestamp(date(2025, 6, 30), 800, 2000),
                EventTimestamp(date(2025, 7, 7), 800, 2000)
            ]
        )

    def test_multiple_weekdays_order(self):
        """Тест порядка следования дней недели"""
        weekends = MultiDateWeekday(weekdays=[6, 7, 5], time=[0, 0])
        result = list(weekends.get_all_timestamps(date(2025, 7, 7), date(2025, 7, 13)))
        self.assertEqual(
            result,
            [
                EventTimestamp(date(2025, 7, 11), 0, 0),  # Пятница
                EventTimestamp(date(2025, 7, 12), 0, 0),  # Суббота
                EventTimestamp(date(2025, 7, 13), 0, 0)   # Воскресенье
            ]
        )

    def test_year_boundary(self):
        """Тест перехода между годами"""
        new_years = MultiDateWeekday(weekdays=[4], time=[1200, 2359])
        result = list(new_years.get_all_timestamps(date(2024, 12, 31), date(2025, 1, 2)))
        self.assertEqual(
            result,
            [EventTimestamp(date(2025, 1, 2), 1200, 2359)]  # Четверг
        )

    def test_time_range_handling(self):
        """Тест обработки диапазона времени"""
        meetings = MultiDateWeekday(weekdays=[3], time=[930, 1045, 1530])
        result = next(meetings.get_all_timestamps(date(2025, 7, 1), date(2025, 7, 31)))
        self.assertEqual(result.st_time, 930)
        self.assertEqual(result.en_time, 1530)

    def test_weekday_wrapping(self):
        """Тест обработки случая, когда первый день после start_date находится в следующей неделе"""
        sundays = MultiDateWeekday(weekdays=[7], time=[0, 0])
        result = list(sundays.get_all_timestamps(date(2025, 7, 13), date(2025, 7, 13)))
        self.assertEqual(
            result,
            [EventTimestamp(date(2025, 7, 13), 0, 0)]
        )

    def test_leap_year(self):
        """Тест високосного года"""
        feb29 = MultiDateWeekday(weekdays=[6], time=[0, 0])
        result = list(feb29.get_all_timestamps(date(2024, 2, 26), date(2024, 3, 3)))
        self.assertEqual(
            result,
            [
                EventTimestamp(date(2024, 3, 2), 0, 0)  # Суббота 2 марта
            ]
        )

    def test_empty_weekdays(self):
        """Тест пустого списка дней недели"""
        empty = MultiDateWeekday(weekdays=[], time=[900, 1700])
        result = list(empty.get_all_timestamps(date(2025, 7, 1), date(2025, 7, 31)))
        self.assertEqual(len(result), 0)

    def test_large_date_range(self):
        """Тест большого диапазона дат"""
        mondays = MultiDateWeekday(weekdays=[1], time=[0, 0])
        result = list(mondays.get_all_timestamps(date(2025, 1, 1), date(2025, 12, 31)))
        self.assertEqual(len(result), 52)  # 52 понедельника в 2025 году

if __name__ == "__main__":
    unittest.main()