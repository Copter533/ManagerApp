import unittest
from abc import abstractmethod
from datetime import date, timedelta
from typing import Iterable, Iterator, Optional

from utils import DebugTimer


class EventTimestamp:
    def __init__(self, when: date, st_time: int, en_time: int):
        self.when = when
        self.st_time = st_time
        self.en_time = en_time

    def __repr__(self):
        return f"{self.when} {self.st_time}-{self.en_time}"

    def __eq__(self, other):
        if not isinstance(other, EventTimestamp): return False
        return (self.when    == other.when    and
                self.st_time == other.st_time and
                self.en_time == other.en_time)

    def __lt__(self, other): return self.when.__lt__(other.when)
    def __gt__(self, other): return self.when.__gt__(other.when)
    def __le__(self, other): return self.when.__le__(other.when)
    def __ge__(self, other): return self.when.__ge__(other.when)


class MultiDateHolder:
    def __init__(self, time: Iterable[int]):
        self.st_time = min(time)
        self.en_time = max(time)

    @abstractmethod
    def get_single_timestamp(self, when_date: date) -> Optional[EventTimestamp]:
        """
            :return: Возвращает дату и время, если событие происходит в when_date,
        """
        raise NotImplementedError()

    @abstractmethod
    def get_all_timestamps(self, start_date: date, end_date: date) -> Iterator[EventTimestamp]:
        """
            :return: Генератор, который выдаёт несортированный список
            дат + времени, когда это событие будет происходить
        """
        raise NotImplementedError()

    def get_next_timestamp(self, when_date: date) -> EventTimestamp:
        """
            :return: Ровно 1 дату, когда произойдёт это событие.
            Дата максимально близко к when_date, но не раньше (может совпадать)
        """
        return next(self.get_all_timestamps(when_date, date(9999, 1, 1)))


class MultiDateWeekday(MultiDateHolder):
    def __init__(self, weekdays: list[int], time):
        super().__init__(time)
        for weekday in weekdays: assert 1 <= weekday <= 7
        self._weekdays = set(weekdays)

    @staticmethod
    def first_weekday(start_date: date, weekday: int) -> date:
        # Переносим в начало недели и двигаем на текущий день недели, результат может быть до start_date
        first_result = start_date + timedelta(days=-start_date.weekday() + weekday - 1)
        # Если получилось до start_date, то переносим на следующую неделю, может быть после end_date
        if first_result < start_date:
            first_result += timedelta(days=7)
        return first_result

    def get_single_timestamp(self, when_date: date):
        if when_date.isoweekday() in self._weekdays:
            return EventTimestamp(when_date, self.st_time, self.en_time)
        return None

    def get_all_timestamps(self, start_date: date, end_date: date):
        week_start = start_date + timedelta(days=-start_date.weekday())
        weeks_count = ((end_date - week_start).days - end_date.weekday()) // 7 + 1

        for _ in range(weeks_count):
            for weekday in self._weekdays:
                day = week_start + timedelta(days=weekday-1)
                if day < start_date: continue
                if day > end_date: break
                yield EventTimestamp(day, 0, 0)
            week_start += timedelta(days=7)

    def get_all_timestamps_OLD(self, start_date: date, end_date: date):
        for weekday in self._weekdays:
            first_result = MultiDateWeekday.first_weekday(start_date, weekday)
            if first_result > end_date: continue # В таком случае в этот день событие не произойдёт

            # Считаем, сколько раз этот день ещё появится
            count = (end_date - first_result).days // 7 + 1

            for i in range(count):
                yield EventTimestamp(first_result + timedelta(days=i*7), self.st_time, self.en_time)

    def get_next_timestamp_OLD(self, when_date: date):
        next_date = None
        for weekday in self._weekdays:
            first_result = MultiDateWeekday.first_weekday(when_date, weekday)
            next_date = first_result if next_date is None else min(next_date, first_result)
        return EventTimestamp(next_date, self.st_time, self.en_time)


class MultiDateMonthday(MultiDateHolder):
    def __init__(self, monthdays: list[int], time):
        super().__init__(time)
        for monthday in monthdays: assert 1 <= monthday <= 31
        self._monthdays = set(monthdays)

    @staticmethod
    def first_monthday(start_date: date, monthday: int) -> date:
        first_result = start_date
        while True:
            try:
                # Кинет ошибку ValueError если такого дня нет в этом месяце
                first_result = first_result.replace(day=monthday)
                # Если получилось до start_date, то переносим на следующий месяц, может быть после end_date
                if first_result >= start_date: return first_result
            except ValueError:
                pass

            if first_result.month == 12:
                first_result = date(first_result.year + 1,
                                    1,
                                    1)
            else:
                first_result = date(first_result.year,
                                    first_result.month + 1,
                                    1)

    def get_single_timestamp(self, when_date: date) -> Optional[EventTimestamp]:
        if when_date.day in self._monthdays:
            return EventTimestamp(when_date, self.st_time, self.en_time)
        return None

    def get_all_timestamps(self, start_date: date, end_date: date):
        for monthday in self._monthdays:
            current = self.first_monthday(start_date, monthday)

            while current <= end_date:
                yield EventTimestamp(current, self.st_time, self.en_time)
                next_month = (
                    date(current.year + 1, 1, 1)
                    if current.month == 12
                    else date(current.year, current.month + 1, 1)
                )
                current = self.first_monthday(next_month, monthday)

    def get_next_timestamp(self, when_date: date):
        next_date = None
        for monthday in self._monthdays:
            first_result = MultiDateMonthday.first_monthday(when_date, monthday)
            next_date = first_result if next_date is None else min(next_date, first_result)
        return EventTimestamp(next_date, self.st_time, self.en_time)


class MultiDateParity(MultiDateHolder):
    def __init__(self, anchor: date, days_on: int, days_off: int, firstly_on=True):
        super().__init__([0, 0])
        self.anchor     = anchor
        self.days_on    = days_on
        self.days_off   = days_off
        self.firstly_on = firstly_on

    # TODO: сделать
    def get_single_timestamp(self, when_date: date):
        raise NotImplementedError()

    def get_all_timestamps(self, start_date: date, end_date: date):
        full_loop = self.days_on + self.days_off
        days_passed = (self.anchor - start_date).days
        closest_anchor = self.anchor
        if days_passed < 0:
            closest_anchor += timedelta(days=(-days_passed // full_loop) * full_loop)

        i = 0
        for _ in range((end_date - closest_anchor).days // full_loop + 1):
            for delta in range(self.days_on):
                date = closest_anchor + timedelta(days=i)
                i += 1
                if date < start_date: continue
                if date > end_date: return
                yield EventTimestamp(date, 0, 0)
            i += self.days_off


def mix_dates_or(gen1: Iterator | list, gen2: Iterator | list):
    """
        ПРЕДПОЛОГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАНОМ ВИДЕ
        также вместо генераторов может быть просто список элементов
    """
    iter1 = iter(gen1)
    iter2 = iter(gen2)
    e1 = next(iter1, None)
    e2 = next(iter2, None)

    while e1 is not None and e2 is not None:
        if e1 < e2:
            yield e1
            e1 = next(iter1, None)
        elif e2 < e1:
            yield e2
            e2 = next(iter2, None)
        else:  # e1 == e2
            yield e1
            e1 = next(iter1, None)
            e2 = next(iter2, None)

    if e1 is not None:
        yield e1
        yield from iter1

    if e2 is not None:
        yield e2
        yield from iter2


def mix_dates_and(gen1: Iterator | list, gen2: Iterator | list):
    """
        ПРЕДПОЛОГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАНОМ ВИДЕ
        также вместо генераторов может быть просто список элементов
    """
    iter1 = iter(gen1)
    iter2 = iter(gen2)

    e1 = next(iter1, None)
    e2 = next(iter2, None)

    while e1 is not None and e2 is not None:
        if e1 == e2:
            yield e1
            e1 = next(iter1, None)
            e2 = next(iter2, None)
        elif e1 < e2:
            e1 = next(iter1, None)
        else:
            e2 = next(iter2, None)


# Основной экран с событиями (время события от даты до даты)
# Мини экран с ожидаемыми событиями (время след. события)


weekends = MultiDateWeekday(
    weekdays=[1, 2, 6, 7],
    time=[0, 0]
)
span_month = date(2025, 8,  1), date(2025, 8, 31)
span_week  = date(2025, 8,  4), date(2025, 8, 10)

with DebugTimer("Eval weekdays"):
    gen1 = (MultiDateWeekday(
        weekdays=[1, 2, 6, 7],
        time=[0, 0]
    ).get_all_timestamps(*span_month))

with DebugTimer("Eval parity"):
    gen2 = (MultiDateParity(
        anchor=date(2025, 8, 1),
        days_on=3,
        days_off=2
    ).get_all_timestamps(*span_month))

with DebugTimer("Condition"):
    gen = tuple(mix_dates_and(gen1, gen2))

print(
    # *gen,
    f"len={len(gen)}",
    sep="\n"
)