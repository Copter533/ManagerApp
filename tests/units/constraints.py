import unittest
from datetime import date, timedelta
from time import time, perf_counter

from multidate_v2 import MultiDateEmpty, constraint_range  # предполагаем, что класс в файле multidate_v2.py


class TestClampToConstraints(unittest.TestCase):

    def test_no_constraints(self):
        holder = MultiDateEmpty()
        start = date(2025, 1, 10)
        end = date(2025, 3, 20)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)),
                         [(start, end)])

    def test_year_constraint_full_inside(self):
        holder = MultiDateEmpty(year_constraint=[2025])
        start = date(2025, 2, 1)
        end = date(2025, 11, 30)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)),
                         [(start, end)])

    def test_year_constraint_clamp_left(self):
        holder = MultiDateEmpty(year_constraint=[2025, 2026])
        start = date(2024, 12, 1)
        end = date(2025, 6, 30)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)),
                         [(date(2025, 1, 1), end)])

    def test_year_constraint_clamp_right(self):
        holder = MultiDateEmpty(year_constraint=[2024])
        start = date(2024, 1, 1)
        end = date(2025, 12, 31)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)),
                         [(start, date(2024, 12, 31))])

    def test_year_constraint_no_overlap(self):
        holder = MultiDateEmpty(year_constraint=[2023])
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), [])

    def test_month_constraint_single_month_match(self):
        holder = MultiDateEmpty(month_constraint=[12])
        start = date(2025, 12, 10)
        end = date(2025, 12, 20)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)),
                         [(start, end)])

    def test_speed(self):
        holder = MultiDateEmpty(month_constraint=[12], year_constraint=[2024])
        start = date(1, 12, 10)
        end = date(9999, 12, 20)

        st = perf_counter()
        for i in range(100):
            self.assertEqual(list(holder.clamp_to_constraints(start, end)),
                             [(date(2024, 12, 1), date(2024, 12, 31))])
        self.assertLess(perf_counter() - st, 0.5, "Слишком медленно!")

    def test_month_constraint_single_month_no_match(self):
        holder = MultiDateEmpty(month_constraint=[1])
        start = date(2025, 12, 10)
        end = date(2025, 12, 20)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), [])

    def test_month_constraint_multiple_months(self):
        holder = MultiDateEmpty(month_constraint=[1, 3, 12])
        start = date(2025, 12, 15)
        end = date(2026, 3, 15)
        expected = [
            (date(2025, 12, 15), date(2026, 1, 31)),
            (date(2026, 3, 1), date(2026, 3, 15)),
        ]
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), sorted(expected))

    def test_month_and_year_constraints(self):
        holder = MultiDateEmpty(month_constraint=[2], year_constraint=[2024, 2026])
        start = date(2025, 1, 1)
        end = date(2026, 12, 31)
        expected = [(date(2026, 2, 1), date(2026, 2, 28))]  # 2024 нет в диапазоне, 2025 февраль не попадает
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), expected)

    def test_periods_constraint_single_period(self):
        holder = MultiDateEmpty(periods_constraint=["2025.06.01-2025.09.30"])
        start = date(2025, 5, 1)
        end = date(2025, 10, 31)
        expected = [(date(2025, 6, 1), date(2025, 9, 30))]
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), expected)

    def test_periods_constraint_multiple_overlapping(self):
        holder = MultiDateEmpty(periods_constraint=[
            "2025.12.01-2026.01.15",
            "2026.01.10-2026.02.20"
        ])
        start = date(2025, 11, 1)
        end = date(2026, 3, 1)
        expected = [(date(2025, 12, 1), date(2026, 2, 20))]
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), expected)

    def test_periods_constraint_non_overlapping(self):
        holder = MultiDateEmpty(periods_constraint=[
            "2025.01.01-2025.01.31",
            "2025.03.01-2025.03.31"
        ])
        start = date(2025, 1, 1)
        end = date(2025, 4, 1)
        expected = [
            (date(2025, 1, 1), date(2025, 1, 31)),
            (date(2025, 3, 1), date(2025, 3, 31))
        ]
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), sorted(expected))

    def test_periods_constraint_no_overlap_with_range(self):
        holder = MultiDateEmpty(periods_constraint=["2024.01.01-2024.12.31"])
        start = date(2025, 1, 1)
        end = date(2025, 12, 31)
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), [])

    def test_all_constraints_combined(self):
        holder = MultiDateEmpty(
            month_constraint=[1, 12],
            year_constraint=[2025],
            periods_constraint=["2025.12.01-2026.01.31"]
        )
        start = date(2025, 11, 1)
        end = date(2026, 2, 1)
        # Год только 2025 → период обрезается до 2025.12.31
        # Месяц 12 подходит, 1 — нет (год 2026 исключён)
        expected = [(date(2025, 12, 1), date(2025, 12, 31))]
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), expected)

    def test_week_parity(self):
        holder = MultiDateEmpty(
            week_parity_constraint=1
        )
        start = date(2026, 1, 1)
        end   = date(2026, 1, 31)
        self.assertEqual(
            list(holder.clamp_to_constraints(start, end)),
            constraint_range(holder, start, end)
        )

    def test_speed_week_parties(self):
        holder = MultiDateEmpty(
            week_parity_constraint=0,
            year_constraint=[2026],
            month_constraint=[1, 2, 3]
        )
        start = date(1, 1, 1)
        end = date(9999, 1, 31)
        self.assertEqual(
            list(holder.clamp_to_constraints(start, end)),
            constraint_range(holder, date(2026, 1, 1), date(2026, 3, 31))
        )

    def test_week_parity_even_only(self):
        holder = MultiDateEmpty(week_parity_constraint=0)  # только чётные недели
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)

        # 2026-01-01 — четверг → неделя 1 (нечётная)
        # Понедельники:
        # 2026-01-05 — начало недели 2 (чётная): 5–11 января
        # 2026-01-12 — начало недели 3 (нечётная)
        # 2026-01-19 — начало недели 4 (чётная): 19–25 января
        # 2026-01-26 — начало недели 5 (нечётная)
        expected = [
            (date(2026, 1, 5), date(2026, 1, 11)),
            (date(2026, 1, 19), date(2026, 1, 25)),
        ]
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))), sorted(expected))

    def test_week_parity_odd_only(self):
        holder = MultiDateEmpty(week_parity_constraint=1)  # только нечётные недели
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)

        expected = [
            (date(2026, 1, 1), date(2026, 1, 4)),    # остаток недели 1
            (date(2026, 1, 12), date(2026, 1, 18)),  # неделя 3
            (date(2026, 1, 26), date(2026, 1, 31)),  # остаток недели 5
        ]
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))), sorted(expected))

    def test_week_parity_with_month_constraint(self):
        holder = MultiDateEmpty(
            month_constraint=[12],
            week_parity_constraint=0  # только чётные недели в декабре
        )
        start = date(2025, 12, 1)
        end = date(2025, 12, 31)

        # Декабрь 2025: понедельник 1 декабря → неделя 49 (2025-W49) — нечётная (49 % 2 = 1)
        # Следующий понедельник: 8 декабря — неделя 50 (чётная)
        # 15 — 51 (нечётная), 22 — 52 (чётная), 29 — 1 2026 (нечётная? нет, 1 % 2 = 1 → нечётная)
        expected = [
            (date(2025, 12, 8), date(2025, 12, 14)),
            (date(2025, 12, 22), date(2025, 12, 28)),
        ]
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))), sorted(expected))

    def test_week_parity_with_year_constraint(self):
        holder = MultiDateEmpty(
            year_constraint=[2026],
            week_parity_constraint=1  # нечётные недели только в 2026
        )
        start = date(2025, 12, 29)  # понедельник — начало недели 1 2026 (нечётная)
        end = date(2026, 1, 15)

        expected = [
            (date(2025, 12, 29), date(2026, 1, 4)),   # неделя 1 (нечётная)
            (date(2026, 1, 12), date(2026, 1, 15)),   # часть недели 3
        ]
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))),
                         constraint_range(holder, start, end))

    def test_week_parity_with_periods(self):
        holder = MultiDateEmpty(
            periods_constraint=["2026.01.01-2026.02.15"],
            week_parity_constraint=0  # чётные недели в периоде
        )
        start = date(2026, 1, 1)
        end = date(2026, 2, 15)

        expected = [
            (date(2026, 1, 5), date(2026, 1, 11)),
            (date(2026, 1, 19), date(2026, 1, 25)),
            (date(2026, 2, 2), date(2026, 2, 8)),     # неделя 6 — чётная
        ]
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))), sorted(expected))

    def test_week_parity_no_constraint_full_range(self):
        holder = MultiDateEmpty()  # без week_parity_constraint
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)
        expected = [(start, end)]
        self.assertEqual(list(holder.clamp_to_constraints(start, end)), expected)

    def test_week_parity_combined_all_constraints(self):
        holder = MultiDateEmpty(
            month_constraint=[1],
            year_constraint=[2026],
            periods_constraint=["2026.01.01-2026.01.31"],
            week_parity_constraint=1  # нечётные недели в январе 2026
        )
        start = date(2026, 1, 1)
        end = date(2026, 1, 31)

        expected = [
            (date(2026, 1, 1), date(2026, 1, 4)),
            (date(2026, 1, 12), date(2026, 1, 18)),
            (date(2026, 1, 26), date(2026, 1, 31)),
        ]
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))), sorted(expected))

if __name__ == '__main__':
    unittest.main()