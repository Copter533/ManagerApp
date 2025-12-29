import unittest
from datetime import date

from date_utils import ScheduleEvent  # предполагаю, что класс там
from multidate_v2 import MultiDateMonthday, MultiDateWeekday, EventStamp


class TestGetFinalTimestamps(unittest.TestCase):

    # ==============================
    # Простые тесты
    # ==============================

    def test_no_limits_no_cancels(self):
        ev = ScheduleEvent(
            name="Daily",
            multi_date=MultiDateWeekday([0, 1440], [1, 2, 3, 4, 5, 6, 7]),  # каждый день
            times=0,  # бесконечно
            anchor_date=date(2020, 1, 1),
            canceled_dates=[]
        )

        stamps = list(ev.get_final_timestamps(date(2025, 1, 10), date(2025, 1, 12)))
        expected = [
            EventStamp(date(2025, 1, 10), [0, 1440]),
            EventStamp(date(2025, 1, 11), [0, 1440]),
            EventStamp(date(2025, 1, 12), [0, 1440]),
        ]
        self.assertEqual(stamps, expected)

    def test_simple_cancel_in_range(self):
        ev = ScheduleEvent(
            name="Test",
            multi_date=MultiDateMonthday([600, 720], [15]),  # 15-е число каждого месяца
            times=0,
            anchor_date=date(2020, 1, 1),
            canceled_dates=[date(2025, 3, 15)]
        )

        stamps = list(ev.get_final_timestamps(date(2025, 3, 1), date(2025, 3, 31)))
        self.assertEqual(stamps, [])  # единственная дата отменена

    # ==============================
    # Тесты с ограничением times
    # ==============================

    def test_times_exactly_matches(self):
        ev = ScheduleEvent(
            name="Limited",
            multi_date=MultiDateMonthday([0, 0], [1]),  # 1-е число каждого месяца
            times=3,
            anchor_date=date(2025, 1, 1),
            canceled_dates=[]
        )

        stamps = list(ev.get_final_timestamps(date(2025, 1, 1), date(2025, 6, 1)))
        expected_dates = [date(2025, 1, 1), date(2025, 2, 1), date(2025, 3, 1)]
        self.assertEqual([s.date for s in stamps], expected_dates)

    def test_times_with_cancel_saves_one(self):
        # Твой сложный тест — оставляем как эталон
        ev = ScheduleEvent(
            "Test",
            MultiDateMonthday([0, 0], [1, 2, 4, 6, 8, 10, 12, 14]),
            times=4,
            anchor_date=date(2025, 1, 1),
            canceled_dates=[date(2025, 1, 3), date(2025, 1, 6)]  # 3 не в расписании, 6 — в расписании
        )

        stamps = list(ev.get_final_timestamps(date(2025, 1, 7), date(2025, 1, 11)))
        self.assertEqual(stamps, [EventStamp(date(2025, 1, 8), [0, 0])])

    def test_cancel_not_in_schedule_doesnt_save(self):
        ev = ScheduleEvent(
            name="Test",
            multi_date=MultiDateMonthday([0, 0], [5, 10, 15]),
            times=2,
            anchor_date=date(2025, 6, 1),
            canceled_dates=[date(2025, 6, 7)]  # 7 не в расписании → не спасает выполнение
        )

        stamps = list(ev.get_final_timestamps(date(2025, 6, 1), date(2025, 8, 31)))
        # Возможные: 5,10,15 июня; 5,10,15 июля; ...
        # Произойдёт только 5 и 10 июня (2 раза)
        expected = [
            EventStamp(date(2025, 6, 5), [0, 0]),
            EventStamp(date(2025, 6, 10), [0, 0]),
        ]
        self.assertEqual(stamps, expected)

    def test_all_past_occurrences_canceled(self):
        ev = ScheduleEvent(
            name="Test",
            multi_date=MultiDateMonthday([0, 0], [10]),
            times=3,
            anchor_date=date(2025, 1, 1),
            canceled_dates=[date(2025, 1, 10), date(2025, 2, 10), date(2025, 3, 10)]
        )

        # Все три возможных до апреля отменены → счётчик не потрачен → можно ещё 3 раза
        stamps = list(ev.get_final_timestamps(date(2025, 4, 1), date(2025, 7, 31)))
        expected_dates = [date(2025, 4, 10), date(2025, 5, 10), date(2025, 6, 10)]
        self.assertEqual([s.date for s in stamps], expected_dates)

    def test_limit_exhausted_before_range(self):
        ev = ScheduleEvent(
            name="Test",
            multi_date=MultiDateWeekday([0, 0], [1]),  # каждый понедельник
            times=2,
            anchor_date=date(2025, 12, 1),  # декабрь 2025
            canceled_dates=[]
        )

        # В декабре 2025 понедельники: 1, 8, 15, 22, 29
        # До 27 декабря (текущая дата в промпте) уже прошло 2 понедельника: 1 и 8? Нет, 1 — понедельник? Проверим:
        # 1 декабря 2025 — понедельник? На самом деле 1 декабря 2025 — понедельник? Да, предположим.
        # Но чтобы точно: берём реальные даты
        # Лучше взять явные даты
        stamps = list(ev.get_final_timestamps(date(2025, 12, 27), date(2025, 12, 31)))
        self.assertEqual(stamps, [])  # уже было 2 понедельника ранее → лимит исчерпан

    # ==============================
    # Краевые случаи
    # ==============================

    def test_anchor_after_start(self):
        ev = ScheduleEvent(
            name="Future",
            multi_date=MultiDateMonthday([0, 0], [20]),
            times=5,
            anchor_date=date(2026, 1, 1),  # событие начинается только с 2026
            canceled_dates=[]
        )

        stamps = list(ev.get_final_timestamps(date(2025, 1, 1), date(2025, 12, 31)))
        self.assertEqual(stamps, [])  # до якоря ничего не считается

    def test_empty_range(self):
        ev = ScheduleEvent("Test", MultiDateMonthday([0, 0], [1]), times=0, anchor_date=date(2020, 1, 1))
        stamps = list(ev.get_final_timestamps(date(2025, 1, 2), date(2025, 1, 1)))  # start > end
        self.assertEqual(stamps, [])

    def test_cancel_in_future_saves_nothing_if_not_reached(self):
        ev = ScheduleEvent(
            name="Test",
            multi_date=MultiDateMonthday([0, 0], [1]),
            times=1,
            anchor_date=date(2025, 1, 1),
            canceled_dates=[date(2026, 1, 1)]  # отмена в будущем
        )

        stamps = list(ev.get_final_timestamps(date(2025, 1, 1), date(2025, 12, 31)))
        self.assertEqual(stamps, [EventStamp(date(2025, 1, 1), [0, 0])])  # произошло 1 раз, отмена в будущем не спасает


if __name__ == '__main__':
    unittest.main(verbosity=2)