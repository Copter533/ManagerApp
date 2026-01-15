import unittest
from datetime import date
from multidate_v2 import MultiDateEmpty
from time_periods import TimePeriod


class TestMultiDatePeriods(unittest.TestCase):

    def test_basic_merge(self):
        """Тест объединения двух смежных периодов"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-03.01.2026",
            "04.01.2026-06.01.2026"
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 6))
        ])

    def test_overlapping_periods(self):
        """Тест объединения пересекающихся периодов"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-05.01.2026",
            "03.01.2026-07.01.2026"
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 7))
        ])

    def test_multiple_overlapping(self):
        """Тест объединения нескольких пересекающихся периодов"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-05.01.2026",
            "03.01.2026-07.01.2026",
            "06.01.2026-10.01.2026"
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 10))
        ])

    def test_non_overlapping_periods(self):
        """Тест, что периоды с разрывом не объединяются"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-03.01.2026",
            "05.01.2026-07.01.2026"  # Разрыв в 1 день (4 января)
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 3)),
            TimePeriod(date(2026, 1, 5), date(2026, 1, 7))
        ])

    def test_unsorted_periods(self):
        """Тест объединения неотсортированных периодов"""
        multidate = MultiDateEmpty(periods_constraint=[
            "05.01.2026-07.01.2026",
            "01.01.2026-03.01.2026",
            "02.01.2026-04.01.2026"  # Пересекается с первыми двумя
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 7))
        ])

    def test_single_day_periods(self):
        """Тест объединения периодов из одного дня"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-01.01.2026",
            "02.01.2026-02.01.2026",
            "03.01.2026-03.01.2026"
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 3))
        ])

    def test_mixed_periods_with_gaps(self):
        """Тест смешанных периодов с разрывами"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-05.01.2026",
            "10.01.2026-12.01.2026",  # Разрыв 4 дня
            "12.01.2026-15.01.2026",  # Смежный с предыдущим
            "20.01.2026-25.01.2026"   # Разрыв 4 дня
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 5)),
            TimePeriod(date(2026, 1, 10), date(2026, 1, 15)),
            TimePeriod(date(2026, 1, 20), date(2026, 1, 25))
        ])

    def test_empty_periods(self):
        """Тест пустого списка периодов"""
        multidate = MultiDateEmpty(periods_constraint=[])
        self.assertEqual(multidate.periods_constraint_dates, [])

    def test_single_period(self):
        """Тест одного периода"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-10.01.2026"
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 10))
        ])

    def test_periods_with_different_years(self):
        """Тест периодов в разных годах"""
        multidate = MultiDateEmpty(periods_constraint=[
            "20.12.2025-05.01.2026",
            "03.01.2026-10.01.2026",
            "15.01.2026-20.01.2026"
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2025, 12, 20), date(2026, 1, 10)), TimePeriod(date(2026, 1, 15), date(2026, 1, 20))
        ])

    def test_touching_periods(self):
        """Тест периодов, которые касаются друг друга (конец одного = начало другого)"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-05.01.2026",
            "05.01.2026-10.01.2026"  # Касаются в точке 5 января
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 10))
        ])

    def test_invalid_period_format(self):
        """Тест обработки некорректного формата периода"""
        with self.assertRaises(ValueError):
            MultiDateEmpty(periods_constraint=[
                "invalid-format",
                "01.01.2026-05.01.2026"
            ])

    def test_merge_with_duplicates(self):
        """Тест объединения дублирующихся периодов"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-05.01.2026",
            "01.01.2026-05.01.2026",  # Дубликат
            "03.01.2026-07.01.2026"
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 7))
        ])

    def test_large_gap_between_periods(self):
        """Тест периодов с большим разрывом"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-10.01.2026",
            "01.02.2026-10.02.2026"  # Разрыв 21 день
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 10)),
            TimePeriod(date(2026, 2, 1), date(2026, 2, 10))
        ])

    def test_periods_with_reverse_order(self):
        """Тест периодов, заданных в обратном порядке (конец раньше начала)"""
        with self.assertRaises(ValueError):
            MultiDateEmpty(periods_constraint=[
                "10.01.2026-01.01.2026"  # Неправильный порядок
            ])

    def test_complex_merge_scenario(self):
        """Сложный сценарий объединения"""
        multidate = MultiDateEmpty(periods_constraint=[
            "01.01.2026-03.01.2026",
            "02.01.2026-04.01.2026",  # Пересекается
            "06.01.2026-06.01.2026",  # Один день, разрыв 1 день
            "07.01.2026-09.01.2026",  # Смежный с предыдущим
            "12.01.2026-15.01.2026",  # Разрыв 2 дня
            "14.01.2026-16.01.2026"   # Пересекается с предыдущим
        ])
        self.assertEqual(multidate.periods_constraint_dates, [
            TimePeriod(date(2026, 1, 1), date(2026, 1, 4)),
            TimePeriod(date(2026, 1, 6), date(2026, 1, 9)),
            TimePeriod(date(2026, 1, 12), date(2026, 1, 16))
        ])


if __name__ == '__main__':
    unittest.main()