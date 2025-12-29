import unittest
from datetime import date, timedelta
from multidate_v2 import MultiDateEmpty  # предполагаем, что класс в файле multidate_v2.py


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
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))), sorted(expected))

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
        self.assertEqual(sorted(list(holder.clamp_to_constraints(start, end))), sorted(expected))

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


if __name__ == '__main__':
    unittest.main()