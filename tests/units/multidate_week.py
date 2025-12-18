import unittest
from datetime import date, timedelta
from multidate_v2 import MultiDateWeekday  # Замените на актуальный путь к вашему модулю

class TestMultiDateWeekday(unittest.TestCase):
    def test_invalid_weekdays(self):
        """Проверка инициализации с некорректными днями недели"""
        with self.assertRaises(AssertionError):
            MultiDateWeekday([0], [10])  # Меньше 1
        with self.assertRaises(AssertionError):
            MultiDateWeekday([8], [10])  # Больше 7
        with self.assertRaises(AssertionError):
            MultiDateWeekday([1, 8], [10])  # Смешанные значения

    def test_empty_time(self):
        """Проверка пустого списка времени"""
        with self.assertRaises(ValueError):
            MultiDateWeekday([1], [])

    def test_single_day_valid(self):
        """Проверка get_single_timestamp для подходящего дня"""
        holder = MultiDateWeekday([1], [10])  # Понедельник
        test_date = date(2023, 10, 2)  # Понедельник (2023-10-02)
        self.assertEqual(holder.get_single_timestamp(test_date), test_date)

    def test_single_day_invalid(self):
        """Проверка get_single_timestamp для неподходящего дня"""
        holder = MultiDateWeekday([1], [10])  # Понедельник
        test_date = date(2023, 10, 3)  # Вторник
        self.assertIsNone(holder.get_single_timestamp(test_date))

    def test_get_all_timestamps_basic(self):
        """Базовая проверка get_all_timestamps с несколькими днями"""
        holder = MultiDateWeekday([1, 3], [10])  # Пн и Ср
        start = date(2023, 10, 1)
        end = date(2023, 10, 10)
        expected = [
            date(2023, 10, 2),  # Пн
            date(2023, 10, 4),  # Ср
            date(2023, 10, 9)   # Пн
        ]
        result = list(holder.get_all_timestamps(start, end))
        self.assertEqual(result, expected)
        self.assertEqual(result, sorted(result))  # Проверка сортировки

    def test_get_all_timestamps_unsorted_weekdays(self):
        """Проверка сортировки при неупорядоченных днях недели"""
        holder = MultiDateWeekday([3, 1], [10])  # Ср и Пн (в обратном порядке)
        start = date(2023, 10, 1)
        end = date(2023, 10, 10)
        expected = [
            date(2023, 10, 2),  # Пн
            date(2023, 10, 4),  # Ср
            date(2023, 10, 9)   # Пн
        ]
        self.assertEqual(list(holder.get_all_timestamps(start, end)), expected)

    def test_get_all_timestamps_edge_week(self):
        """Проверка на границе недели"""
        holder = MultiDateWeekday([7], [10])  # Воскресенье
        start = date(2023, 10, 7)  # Суббота
        end = date(2023, 10, 8)    # Воскресенье
        expected = [date(2023, 10, 8)]
        self.assertEqual(list(holder.get_all_timestamps(start, end)), expected)

    def test_count_timestamps_single_day(self):
        """Проверка count_timestamps для одного дня"""
        holder = MultiDateWeekday([1], [10])  # Понедельник
        d = date(2023, 10, 2)  # Понедельник
        self.assertEqual(holder.count_timestamps(d, d), 1)

    def test_count_timestamps_no_occurrence(self):
        """Проверка count_timestamps когда событий нет"""
        holder = MultiDateWeekday([2], [10])  # Вторник
        d = date(2023, 10, 2)  # Понедельник
        self.assertEqual(holder.count_timestamps(d, d), 0)

    def test_count_timestamps_multiple_weeks(self):
        """Проверка подсчёта событий через несколько недель"""
        holder = MultiDateWeekday([1], [10])  # Понедельник
        start = date(2023, 10, 2)
        end = date(2023, 10, 16)
        self.assertEqual(holder.count_timestamps(start, end), 3)  # 2, 9, 16 октября

    def test_count_timestamps_first_after_end(self):
        """Проверка случая когда первое событие после end_date"""
        holder = MultiDateWeekday([5], [10])  # Пятница
        start = date(2023, 10, 7)  # Суббота
        end = date(2023, 10, 7)
        self.assertEqual(holder.count_timestamps(start, end), 0)

    def test_get_next_timestamp_same_day(self):
        """Проверка get_next_timestamp для текущего дня"""
        holder = MultiDateWeekday([1], [10])  # Понедельник
        d = date(2023, 10, 2)  # Понедельник
        self.assertEqual(holder.get_next_timestamp(d), d)

    def test_get_next_timestamp_future(self):
        """Проверка get_next_timestamp для будущего события"""
        holder = MultiDateWeekday([1], [10])  # Понедельник
        d = date(2023, 10, 3)  # Вторник
        self.assertEqual(holder.get_next_timestamp(d), date(2023, 10, 9))

    def test_get_next_timestamp_no_future(self):
        """Проверка get_next_timestamp когда событий больше нет"""
        holder = MultiDateWeekday([7], [10])  # Воскресенье
        d = date(9999, 12, 31)
        self.assertIsNone(holder.get_next_timestamp(d))

    def test_empty_range(self):
        """Проверка пустого диапазона дат"""
        holder = MultiDateWeekday([1], [10])
        start = date(2023, 10, 3)
        end = date(2023, 10, 4)
        self.assertEqual(list(holder.get_all_timestamps(start, end)), [])
        self.assertEqual(holder.count_timestamps(start, end), 0)

    def test_week_boundary(self):
        """Проверка на границе недель (крайний случай из original code)"""
        holder = MultiDateWeekday([1, 5], [10])  # Пн и Пт
        start = date(2023, 10, 2)  # Пн
        end = date(2023, 10, 6)    # Пт
        expected = [
            date(2023, 10, 2),  # Пн
            date(2023, 10, 6)   # Пт
        ]
        self.assertEqual(list(holder.get_all_timestamps(start, end)), expected)

    def test_multiple_weeks_edge(self):
        """Проверка события в последний день диапазона"""
        holder = MultiDateWeekday([7], [10])  # Воскресенье
        start = date(2023, 10, 1)
        end = date(2023, 10, 8)  # Воскресенье
        self.assertEqual(holder.count_timestamps(start, end), 2)
        self.assertEqual(
            list(holder.get_all_timestamps(start, end)),
            [date(2023, 10, 1), date(2023, 10, 8)]
        )

    def test_non_consecutive_days(self):
        """Проверка несмежных дней недели в одной неделе"""
        holder = MultiDateWeekday([2, 5], [10])  # Вт и Пт
        start = date(2023, 10, 1)
        end = date(2023, 10, 7)
        expected = [
            date(2023, 10, 3),  # Вт
            date(2023, 10, 6)   # Пт
        ]
        self.assertEqual(list(holder.get_all_timestamps(start, end)), expected)

    def test_year_boundary(self):
        """Проверка перехода через новогодние каникулы"""
        holder = MultiDateWeekday([7], [10])  # Воскресенье
        start = date(2023, 12, 25)
        end = date(2024, 1, 1)
        expected = [
            date(2023, 12, 31),  # Воскресенье 2023
            date(2024, 1, 7)     # Но это уже после end_date
        ]
        result = list(holder.get_all_timestamps(start, end))
        self.assertEqual(result, [date(2023, 12, 31)])
        self.assertEqual(holder.count_timestamps(start, end), 1)


if __name__ == '__main__':
    unittest.main()