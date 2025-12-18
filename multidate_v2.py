import unittest
from abc import abstractmethod
from datetime import date, timedelta, datetime
from typing import Iterable, Iterator, Optional

from utils import DebugTimer


# Событие, которое происходит несколько раз в 1 день (в разное время) считается как 1 раз
class MultiDateHolder:
    @abstractmethod
    def is_happening(self, when_date: date) -> bool:
        """
            :return: Возвращает True, если событие происходит в when_date,
        """
        raise NotImplementedError()

    @abstractmethod
    def get_all_timestamps(self, start_date: date, end_date: date) -> Iterator[date]:
        """
            :return: Генератор, который выдаёт СОРТИРОВАНЫЙ ПО ВОЗРАСТАНИЮ список
            дат + времени, когда это событие будет происходить
        """
        raise NotImplementedError()

    @abstractmethod
    def count_timestamps(self, start_date: date, end_date: date) -> int:
        """
            :return: Выдаёт кол-во раз (кол-во дней) когда событие произойдёт в
            заданный промежуток времени
        """
        raise NotImplementedError()

    def get_next_timestamp(self, when_date: date) -> Optional[date]:
        """
            :return: Ровно 1 дату, когда произойдёт это событие.
            Дата максимально близко к when_date, но не раньше (может совпадать)
        """
        return next(self.get_all_timestamps(when_date, date(9999, 1, 1)), None)


class MultiDateWeekday(MultiDateHolder):
    def __init__(self, weekdays: list[int]):
        super().__init__()
        for weekday in weekdays: assert 1 <= weekday <= 7, "День недели должен быть от 1 до 7"
        self._weekdays = tuple(sorted(set(weekdays)))

    def is_happening(self, when_date: date):
        return when_date.isoweekday() in self._weekdays

    def get_all_timestamps(self, start_date: date, end_date: date):
        week_start = start_date + timedelta(days=-start_date.weekday())
        weeks_count = ((end_date - week_start).days - end_date.weekday()) // 7 + 1

        for _ in range(weeks_count):
            for weekday in self._weekdays:
                day = week_start + timedelta(days=weekday-1)
                if day < start_date: continue
                if day > end_date: break
                yield day
            week_start += timedelta(days=7)

    def count_timestamps(self, start_date: date, end_date: date):
        count = 0
        for weekday in self._weekdays:
            # Переносим в начало недели и двигаем на текущий день недели, результат может быть до start_date
            first_result = start_date + timedelta(days=-start_date.weekday() + weekday - 1)
            # Если получилось до start_date, то переносим на следующую неделю, может быть после end_date
            if first_result < start_date: first_result += timedelta(days=7)
            # В таком случае в этот день событие не произойдёт
            if first_result > end_date: continue
            # Считаем, сколько раз этот день ещё появится
            count += (end_date - first_result).days // 7 + 1
        return count


class MultiDateMonthday(MultiDateHolder):
    def __init__(self, monthdays: list[int]):
        for monthday in monthdays: assert 1 <= monthday <= 31, "День месяца должен быть от 1 до 31"
        self._monthdays = tuple(sorted(set(monthdays)))

    def is_happening(self, when_date: date):
        return when_date.day in self._monthdays

    def get_all_timestamps(self, start_date: date, end_date: date):
        cursor = index = None
        for start_date in (start_date, (start_date.replace(day=1) + timedelta(days=31)).replace(day=1)):
            if start_date > end_date: return
            for index, monthday in enumerate(self._monthdays):
                if start_date.day > monthday: continue
                try:
                    cursor = start_date.replace(day=monthday)
                except ValueError:
                    continue
                else:
                    break
            else:
                # st = 2025.10.30, days = [1]
                # st2 = 2025.11.01
                continue
            break
        else:
            return

        while cursor <= end_date:
            yield cursor
            index += 1
            if index < len(self._monthdays):
                try:
                    cursor = cursor.replace(day=self._monthdays[index])
                except ValueError:
                    pass
                else:
                    continue
            index = 0

            while cursor <= end_date:
                cursor = (cursor.replace(day=1) + timedelta(days=31))
                try:
                    cursor = cursor.replace(day=self._monthdays[0])
                    break
                except ValueError:
                    continue

    def count_timestamps(self, start_date: date, end_date: date) -> int:
        count = 0
        for monthday in self._monthdays[::-1]:
            try:
                check_day = start_date.replace(day=monthday)
                if check_day > end_date: continue
                if check_day < start_date: break
                count += 1
            except ValueError:
                continue

        if start_date.replace(day=1) != end_date.replace(day=1):
            for monthday in self._monthdays:
                try:
                    check_day = end_date.replace(day=monthday)
                    if check_day > end_date: break
                    if check_day < start_date: continue
                    count += 1
                except ValueError:
                    break

        monthdays_count = len(self._monthdays)
        # 2025 - 12 -> 2026 - 1
        max_offset = (end_date.month - start_date.month) + (end_date.year - start_date.year) * 12
        # Некоторых этих дат может не существовать в месяце
        important_days = [day for day in self._monthdays if day >= 28]

        if important_days:
            cursor = start_date.replace(day=1)
            for offset in range(1, max_offset):
                cursor = (cursor + timedelta(days=31)).replace(day=1)
                unprocessed_count = len(important_days)
                for monthday in important_days:
                    try:
                        cursor.replace(day=monthday)  # Кидает ValueError если дата не верна
                        unprocessed_count -= 1
                    except ValueError:
                        break
                count += monthdays_count - unprocessed_count
        elif max_offset >= 1:
            count += (max_offset - 1) * monthdays_count

        return count


class MultiDateParity(MultiDateHolder):
    def __init__(self, anchor: date, days_on: int, days_off: int, firstly_on=True):
        self.anchor     = anchor
        self.days_on    = days_on
        self.days_off   = days_off
        self.firstly_on = firstly_on

    def is_happening(self, when_date: date) -> bool:
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
                yield date
            i += self.days_off

    def count_timestamps(self, start_date: date, end_date: date) -> int:
        raise NotImplementedError()


class AllTimestampsWrapper:
    def __init__(self, holder: MultiDateHolder, st_date: date, en_date: date):
        self.generator = holder.get_all_timestamps(st_date, en_date)

    def __mul__(self, other):  # and -> *
        if not isinstance(other, AllTimestampsWrapper): raise TypeError
        return mix_dates_and(self.generator, other.generator)

    def __add__(self, other):  # or -> +
        if not isinstance(other, AllTimestampsWrapper): raise TypeError
        return mix_dates_or(self.generator, other.generator)


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


def mix_dates_or_multi(*gens: Iterator | list):
    """
        ПРЕДПОЛОГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАНОМ ВИДЕ
        также вместо генераторов может быть просто список элементов
    """
    iters = [iter(gen) for gen in gens]
    elems = [next(it, None) for it in iters]

    while True:
        # Фильтруем активные элементы (игнорируем None)
        valid_vals = [c for c in elems if c is not None]
        if not valid_vals:
            break

        min_val = min(valid_vals)
        yield min_val

        # Обновляем все итераторы, содержащие текущий минимальный элемент
        for i in range(len(elems)):
            if elems[i] == min_val:
                elems[i] = next(iters[i], None)


def mix_dates_and_multi(*gens: Iterator | list):
    """
        ПРЕДПОЛОГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАНОМ ВИДЕ
        также вместо генераторов может быть просто список элементов
    """
    iters = [iter(i) for i in gens]
    elems = [next(e, None) for e in iters]

    while all(e is not None for e in elems):
        min_e = min(elems)
        max_e = max(elems)
        if min_e == max_e:
            yield min_e
            elems = [next(e, None) for e in iters]
        else:
            # e1 < e2 ->
            # min_e = e1 ->
            # e1, next
            elems = [next(e, None) if min_e >= elems[i] else elems[i] for i, e in enumerate(iters)]


# Основной экран с событиями (время события от даты до даты)
# Мини экран с ожидаемыми событиями (время след. события)


class MultiDateMixer(MultiDateHolder):

    def __init__(self, holders: Iterable[MultiDateHolder] | MultiDateHolder, formula: str = None):
        self.reducers = []
        self.holders = tuple(holders) if isinstance(holders, Iterable) else (holders,)
        # Если формула None, то все объекты будут объеденины (т.е. A + B + C ... + X)
        self.formula = None if formula is None else formula.replace("and", "*").replace("or", "+")

    def month_reducer(self, months):
        self.reducers = []

    def _get_timestamps_iterator(self, start_date: date, end_date: date):
        return (holder.get_all_timestamps(start_date, end_date) for holder in self.holders)

    def is_happening(self, when_date: date) -> bool:
        return all(holder.is_happening(when_date) for holder in self.holders)

    def count_timestamps(self, start_date: date, end_date: date) -> int:
        if len(self.holders) == 1:
            return self.holders[0].count_timestamps(start_date, end_date)
        return len(tuple(self.get_all_timestamps(start_date, end_date)))

    def get_all_timestamps(self, start_date: date, end_date: date) -> Iterator[date]:
        if len(self.holders) == 1:
            yield from self.holders[0].get_all_timestamps(start_date, end_date)
        elif self.formula is None:
            yield from mix_dates_or_multi(
                *(holder.get_all_timestamps(start_date, end_date) for holder in self.holders))
        else:
            variables = {
                chr(ord("A") + i): AllTimestampsWrapper(holder, start_date, end_date)
                for i, holder in enumerate(self.holders)
            }
            yield from eval(self.formula, variables)

    def display_calendar(self, anchor_date=datetime.now().date(), week_range_before=2, week_range_after=2):
        en_date = anchor_date + timedelta(days=-anchor_date.weekday() + 7 * week_range_after + 6)
        st_date = anchor_date - timedelta(days=+anchor_date.weekday() + 7 * week_range_before)

        target_dates = set(self.get_all_timestamps(st_date, en_date))

        print("Пн Вт Ср Чт Пт Сб Вс")
        for i in range((en_date - st_date).days + 1):
            current_date = st_date + timedelta(days=i)
            if current_date in target_dates:
                color = '92'
            elif current_date.month != anchor_date.month:
                color = '90'
            else:
                color = '97'

            if current_date == anchor_date:
                color = f'4{color[1]};30'

            print(f'\033[{color}m{current_date.day:02d}\033[0m', end=' \n'[int(i % 7 == 6)])


mixer = MultiDateMixer(
    [
        MultiDateParity(date(2025, 8, 28), 3, 2),
        MultiDateWeekday([1, 2, 3, 4, 5])
    ], formula="A and B"
)

mixer.display_calendar(week_range_after=7)