import unittest
from datetime import date, timedelta
from multidate_v2 import MultiDateParity, EventStamp


class TestMultiDateParityTimestamps(unittest.TestCase):

    def test_basic_pattern_firstly_on(self):
        """Базовый паттерн: 2 дня работы, 3 дня перерыва"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 15)

        result = list(holder.get_all_timestamps(start, end))

        # Проверка количества
        self.assertEqual(len(result), 6)
        self.assertEqual(holder.count_timestamps(start, end), 6)

        # Проверка конкретных дат
        expected_dates = [
            date(2023, 10, 1), date(2023, 10, 2),  # Цикл 1
            date(2023, 10, 6), date(2023, 10, 7),  # Цикл 2
            date(2023, 10, 11), date(2023, 10, 12)  # Цикл 3
        ]
        self.assertEqual([s.date for s in result], expected_dates)

        # Проверка сортировки
        self.assertEqual([s.date for s in result], sorted([s.date for s in result]))

    def test_basic_pattern_firstly_off(self):
        """Паттерн начинающийся с OFF периода"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=False)

        # Ответы: 3 4 5  8 9 10  13 14 15
        start = date(2023, 10, 1)
        end = date(2023, 10, 15)

        result = list(holder.get_all_timestamps(start, end))

        self.assertEqual(len(result), 9)
        self.assertEqual(holder.count_timestamps(start, end), 9)

    def test_anchor_far_in_past(self):
        """Якорь давно в прошлом - проверка корректного вычисления цикла"""
        anchor = date(2020, 1, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=5, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 21)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        self.assertEqual(len(result), count)
        self.assertGreater(count, 0)

        # Проверяем что все даты в диапазоне
        for stamp in result:
            self.assertTrue(start <= stamp.date <= end)

    def test_anchor_in_future(self):
        """События всё равно быть должны"""
        anchor = date(2024, 1, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 12, 31)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        self.assertEqual(count, 36)
        self.assertEqual(count, len(result))

    def test_single_day_pattern(self):
        """Паттерн: 1 день работы, N дней перерыва"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=1, days_off=6, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 29)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        expected_dates = [
            date(2023, 10, 1),
            date(2023, 10, 8),
            date(2023, 10, 15),
            date(2023, 10, 22),
            date(2023, 10, 29)
        ]

        self.assertEqual(len(result), 5)
        self.assertEqual(count, 5)
        self.assertEqual([s.date for s in result], expected_dates)

    def test_start_in_middle_of_on_period(self):
        """Начало диапазона в середине ON периода"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=5, days_off=2, firstly_on=True)

        start = date(2023, 10, 3)  # День 2 ON периода
        end = date(2023, 10, 10)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        expected_dates = [
            date(2023, 10, 3), date(2023, 10, 4), date(2023, 10, 5),  # Остаток 1-го цикла
            # 6, 7 - OFF
            date(2023, 10, 8), date(2023, 10, 9), date(2023, 10, 10)  # Начало 2-го цикла
        ]

        self.assertEqual(len(result), 6)
        self.assertEqual(count, 6)
        self.assertEqual([s.date for s in result], expected_dates)

    def test_start_in_middle_of_off_period(self):
        """Начало диапазона в середине OFF периода"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=5, firstly_on=True)

        # Ответы: 8 9  15

        start = date(2023, 10, 4)  # День 3 цикла (в OFF периоде)
        end = date(2023, 10, 15)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        expected_dates = [
            # Ждем конца OFF периода
            date(2023, 10, 8), date(2023, 10, 9),  # Цикл 2
            date(2023, 10, 15)
        ]

        self.assertEqual(len(result), 3)
        self.assertEqual(count, 3)
        self.assertEqual([s.date for s in result], expected_dates)

    def test_empty_range(self):
        """Пустой диапазон (start > end)"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=True)

        start = date(2023, 10, 10)
        end = date(2023, 10, 5)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        self.assertEqual(len(result), 0)
        self.assertEqual(count, 0)

    def test_single_day_range_on_event(self):
        """Диапазон из одного дня (день события)"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=3, days_off=4, firstly_on=True)

        start = end = date(2023, 10, 2)  # День 1 ON периода

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        self.assertEqual(len(result), 1)
        self.assertEqual(count, 1)
        self.assertEqual(result[0].date, date(2023, 10, 2))

    def test_single_day_range_off_period(self):
        """Диапазон из одного дня (день OFF периода)"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=5, firstly_on=True)

        start = end = date(2023, 10, 5)  # День OFF периода

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        self.assertEqual(len(result), 0)
        self.assertEqual(count, 0)

    def test_year_boundary(self):
        """Переход через границу года"""
        anchor = date(2023, 12, 29)
        holder = MultiDateParity([10, 0], anchor, days_on=3, days_off=2, firstly_on=True)

        start = date(2023, 12, 29)
        end = date(2024, 1, 10)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        expected_dates = [
            date(2023, 12, 29), date(2023, 12, 30), date(2023, 12, 31),  # Цикл 1
            # 1, 2 янв - OFF
            date(2024, 1, 3), date(2024, 1, 4), date(2024, 1, 5),  # Цикл 2
            # 6, 7 янв - OFF
            date(2024, 1, 8), date(2024, 1, 9), date(2024, 1, 10)  # Цикл 3
        ]

        self.assertEqual(len(result), 9)
        self.assertEqual(count, 9)
        self.assertEqual([s.date for s in result], expected_dates)

    def test_long_cycle(self):
        """Длинный цикл (10 дней ON, 20 дней OFF)"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=10, days_off=20, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 11, 30)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        # Цикл = 30 дней. С 1 окт по 30 ноя = 60 дней = 2 полных цикла
        self.assertEqual(len(result), 21)  # 10 + 10
        self.assertEqual(count, 21)

        # Первые 10 должны быть подряд
        for i in range(10):
            self.assertEqual(result[i].date, date(2023, 10, 1) + timedelta(days=i))

    def test_multiple_full_cycles(self):
        """Несколько полных циклов"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 25)  # Ровно 5 циклов

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        # 5 циклов * 2 дня = 10 событий
        self.assertEqual(len(result), 10)
        self.assertEqual(count, 10)

    def test_event_stamp_contains_time(self):
        """Проверка что EventStamp содержит правильное время"""
        anchor = date(2023, 10, 1)
        time = [14, 30]
        holder = MultiDateParity(time, anchor, days_on=2, days_off=1, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 5)

        result = list(holder.get_all_timestamps(start, end))

        # Проверяем что у каждого EventStamp правильное время
        for stamp in result:
            self.assertEqual(stamp.time, time)

    def test_exact_cycle_boundary(self):
        """Точная граница цикла"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=3, days_off=4, firstly_on=True)

        # Один цикл = 7 дней (3 ON + 4 OFF)
        start = date(2023, 10, 1)
        end = date(2023, 10, 7)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        # Должны быть только 3 дня ON из первого цикла
        self.assertEqual(len(result), 3)
        self.assertEqual(count, 3)
        self.assertEqual([s.date for s in result], [
            date(2023, 10, 1),
            date(2023, 10, 2),
            date(2023, 10, 3)
        ])

    def test_range_ending_in_middle_of_on(self):
        """Конец диапазона в середине ON периода"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=5, days_off=2, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 10)  # День 2 второго ON периода

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        expected_dates = [
            date(2023, 10, 1), date(2023, 10, 2), date(2023, 10, 3),
            date(2023, 10, 4), date(2023, 10, 5),  # Первый цикл (5 дней)
            # 6, 7 - OFF
            date(2023, 10, 8), date(2023, 10, 9), date(2023, 10, 10)  # Часть второго цикла
        ]

        self.assertEqual(len(result), 8)
        self.assertEqual(count, 8)
        self.assertEqual([s.date for s in result], expected_dates)

    def test_very_short_range_with_event(self):
        """Очень короткий диапазон с одним событием"""
        anchor = date(2023, 10, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=1, days_off=10, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 1)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        self.assertEqual(len(result), 1)
        self.assertEqual(count, 1)

    def test_events_before_anchor(self):
        """События должны происходить и ДО якоря"""
        anchor = date(2023, 10, 15)  # Якорь в середине
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=True)

        # Запрашиваем диапазон ДО якоря
        start = date(2023, 10, 1)
        end = date(2023, 10, 14)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        # Цикл = 5 дней (2 ON + 3 OFF)
        # Работаем НАЗАД от якоря:
        # Якорь 15 окт - начало цикла
        # Предыдущий цикл начинается 10 окт: [10,11 ON] [12,13,14 OFF]
        # Еще предыдущий начинается 5 окт: [5,6 ON] [7,8,9 OFF]
        # Еще предыдущий начинается 30 сент (вне диапазона)
        # Но нужно понять: [1,2 ??] [3,4,5 ??]...

        # Правильный подсчет от якоря назад:
        # 15 окт - цикл 0: [15,16 ON]
        # 10 окт - цикл -1: [10,11 ON] [12,13,14 OFF]
        # 5 окт - цикл -2: [5,6 ON] [7,8,9 OFF]
        # 30 сент - цикл -3: [30 сент, 1 окт ON] [2,3,4 OFF]
        # 25 сент - цикл -4: вне диапазона

        # В диапазоне [1 окт, 14 окт]:
        # 1 окт (ON), 5,6 (ON), 10,11 (ON)
        expected_dates = [
            date(2023, 10, 1),
            date(2023, 10, 5), date(2023, 10, 6),
            date(2023, 10, 10), date(2023, 10, 11)
        ]

        self.assertEqual(len(result), 5)
        self.assertEqual(count, 5)
        self.assertEqual([s.date for s in result], expected_dates)

    def test_events_spanning_anchor(self):
        """События до, во время и после якоря"""
        anchor = date(2023, 10, 10)
        holder = MultiDateParity([10, 0], anchor, days_on=3, days_off=2, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 20)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        # Цикл = 5 дней (3 ON + 2 OFF)
        # От якоря 10 окт:
        # Цикл 0: [10,11,12 ON] [13,14 OFF]
        # Цикл 1: [15,16,17 ON] [18,19 OFF]
        # Цикл 2: [20... ON]

        # Назад от якоря:
        # Цикл -1: [5,6,7 ON] [8,9 OFF]
        # Цикл -2: [30 сент, 1 окт, 2 окт ON] [3,4 окт OFF]

        expected_dates = [
            date(2023, 10, 1), date(2023, 10, 2),  # Цикл -2
            date(2023, 10, 5), date(2023, 10, 6), date(2023, 10, 7),  # Цикл -1
            date(2023, 10, 10), date(2023, 10, 11), date(2023, 10, 12),  # Цикл 0
            date(2023, 10, 15), date(2023, 10, 16), date(2023, 10, 17),  # Цикл 1
            date(2023, 10, 20)  # Цикл 2
        ]

        self.assertEqual(len(result), len(expected_dates))
        self.assertEqual(count, len(expected_dates))
        self.assertEqual([s.date for s in result], expected_dates)

    def test_anchor_at_end_of_range(self):
        """Якорь в конце диапазона - все события до него"""
        anchor = date(2023, 10, 20)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=True)

        # Ответы: 1  5 6  10 11  15 16  20
        start = date(2023, 10, 1)
        end = date(2023, 10, 20)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        expected_dates = [
            date(2023, 10, 1),
            date(2023, 10, 5), date(2023, 10, 6),
            date(2023, 10, 10), date(2023, 10, 11),
            date(2023, 10, 15), date(2023, 10, 16),
            date(2023, 10, 20)
        ]

        self.assertEqual(len(result), len(expected_dates))
        self.assertEqual(count, len(expected_dates))
        self.assertEqual([s.date for s in result], expected_dates)

    def test_only_before_anchor(self):
        """Только события до якоря, якорь вне диапазона"""
        anchor = date(2023, 11, 1)
        holder = MultiDateParity([10, 0], anchor, days_on=3, days_off=4, firstly_on=True)

        start = date(2023, 10, 1)
        end = date(2023, 10, 31)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        # Цикл = 7 дней (3 ON + 4 OFF)
        # Якорь 1 ноя
        # Назад: 25окт, 18окт, 11окт, 4окт, 27сент
        # В диапазоне [1-31 окт]:
        # Цикл от 27 сент: [27,28,29 сент] [30 сент, 1,2,3 окт OFF]
        # Цикл от 4 окт: [4,5,6 ON] [7,8,9,10 OFF]
        # Цикл от 11 окт: [11,12,13 ON] [14,15,16,17 OFF]
        # Цикл от 18 окт: [18,19,20 ON] [21,22,23,24 OFF]
        # Цикл от 25 окт: [25,26,27 ON] [28,29,30,31 OFF]

        expected_dates = [
            date(2023, 10, 4), date(2023, 10, 5), date(2023, 10, 6),
            date(2023, 10, 11), date(2023, 10, 12), date(2023, 10, 13),
            date(2023, 10, 18), date(2023, 10, 19), date(2023, 10, 20),
            date(2023, 10, 25), date(2023, 10, 26), date(2023, 10, 27)
        ]

        self.assertEqual(len(result), 12)
        self.assertEqual(count, 12)
        self.assertEqual([s.date for s in result], expected_dates)

    def test_firstly_off_before_anchor(self):
        """firstly_on=False и события до якоря"""
        anchor = date(2023, 10, 15)
        holder = MultiDateParity([10, 0], anchor, days_on=2, days_off=3, firstly_on=False)

        start = date(2023, 10, 1)
        end = date(2023, 10, 20)

        result = list(holder.get_all_timestamps(start, end))
        count = holder.count_timestamps(start, end)

        # firstly_on=False: [SKIP 2] [ON 3]
        # Якорь 15 окт - начало SKIP периода
        # От якоря: [15,16 SKIP] [17,18,19 ON] [20,21 SKIP]...

        # Назад от якоря (циклы по 5 дней):
        # Цикл -1 начало 10 окт: [10,11 SKIP] [12,13,14 ON]
        # Цикл -2 начало 5 окт: [5,6 SKIP] [7,8,9 ON]
        # Цикл -3 начало 30 сент: [30 сент, 1 окт SKIP] [2,3,4 ON]

        expected_dates = [
            date(2023, 10, 2), date(2023, 10, 3), date(2023, 10, 4),
            date(2023, 10, 7), date(2023, 10, 8), date(2023, 10, 9),
            date(2023, 10, 12), date(2023, 10, 13), date(2023, 10, 14),
            date(2023, 10, 17), date(2023, 10, 18), date(2023, 10, 19)
        ]

        self.assertEqual(len(result), 12)
        self.assertEqual(count, 12)
        self.assertEqual([s.date for s in result], expected_dates)


if __name__ == '__main__':
    unittest.main()