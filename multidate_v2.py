import bisect
import re
from abc import abstractmethod, ABC, ABCMeta
from datetime import date, timedelta, datetime
from itertools import starmap
from math import ceil
from typing import Iterable, Iterator, Optional, Any, Generator

from time_periods import all_periods, TimePeriod
from utils import tuple_range_to_str, word_case, DebugTimer, tuple_range_to_ranges

days_of_week = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС']
months = [
            ['января',   'январе',   'январь',   'янв'],
            ['февраля',  'феврале',  'февраль',  'фев'],
            ['марта',    'марте',    'март',     'мар'],
            ['апреля',   'апреле',   'апрель',   'апр'],
            ['мая',      'мае',      'май',      'май'],
            ['июня',     'июне',     'июнь',     'июн'],
            ['июля',     'июле',     'июль',     'июл'],
            ['августа',  'августе',  'август',   'авг'],
            ['сентября', 'сентябре', 'сентябрь', 'сен'],
            ['октября',  'октябре',  'октябрь',  'окт'],
            ['ноября',   'ноябре',   'ноябрь',   'ноя'],
            ['декабря',  'декабре',  'декабрь',  'дек']
        ]


def str_to_datetime(when: str):
    day, month, year = tuple(map(int, when.split('.')))[::-1]
    if year > 1000:
        return datetime(year, month, day)
    else:
        return datetime(day, month, year)

def datetime_to_str(when: date | datetime):
    return f'{when.day}.{when.month}.{when.year}'

def time_stamp_to_str(stamp: list[int], mid="-"):
    if stamp is None: return None
    if isinstance(stamp, str): return stamp
    h1, m1 = map(int, divmod(stamp[0], 60))
    h2, m2 = map(int, divmod(stamp[1], 60))
    return f'{h1}:{"0" if m1 < 10 else ""}{m1}{mid}{h2}:{"0" if m2 < 10 else ""}{m2}'


def month_end(day: date):
    return (day.replace(day=1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)


class EventStamp:
    def __init__(self, date: date, time):
        if len(time) != 2: raise ValueError(f"Неверно задано время: {time}")
        self.date = date
        self.time = time

    def __lt__(self, other): return self.date.__lt__(other.date)
    def __le__(self, other): return self.date.__le__(other.date)
    def __gt__(self, other): return self.date.__gt__(other.date)
    def __ge__(self, other): return self.date.__ge__(other.date)
    def __eq__(self, other): return self.date.__eq__(other.date)

    def __repr__(self):
        return f"{datetime_to_str(self.date)} {time_stamp_to_str(self.time)}"

    def get_date(self): return self.date
    def get_time(self): return self.time

    def get_start_datetime(self):
        return datetime(self.date.year, self.date.month, self.date.day) + timedelta(minutes=self.time[0])

    def get_end_datetime(self):
        return datetime(self.date.year, self.date.month, self.date.day) + timedelta(minutes=self.time[1])

    def as_datetimes(self) -> tuple[datetime, datetime]:
        return self.get_start_datetime(), self.get_end_datetime()


# Событие, которое происходит несколько раз в 1 день (в разное время) считается как 1 раз
class MultiDateHolder(ABC):
    """
    Правила соединения общих временных рамок:
     - Рамки одного и того же типа (например 3 и 7 месяц) объединяются
     - Рамки разных типов (например (3 и 7 месяц) и 2025 год) пересекаются
     Т.е:
     (M1 + M2 + ... + Mx) * (Y1 + Y2 + ... + Yx) * (P1 + P2 + ... + Px) * week_parity
    """
    def __init__(self, time: list[int] | tuple[int, int],
                 month_constraint=None, year_constraint=None, periods_constraint=None, week_parity_constraint=None):
        if len(time) != 2: raise ValueError(f"Неверно задано время: {time}")
        self.time = time

        self.month_constraint: list[int] = [] if month_constraint is None else sorted(set(month_constraint))
        self.year_constraint:  list[int] = [] if year_constraint  is None else sorted(set(year_constraint))

        self.week_parity_constraint = week_parity_constraint

        self.periods_constraint = periods_constraint or []

        self.periods_constraint_dates: list[TimePeriod] = []
        if self.periods_constraint:
            self._merge_periods()

    def _merge_periods(self):
        periods_starts = []
        periods_ends   = []
        for period in self.periods_constraint:
            old_count = len(periods_starts)

            if not isinstance(period, str):
                raise ValueError(f"Неверно задан период: {period} (ожидается строка, получен {type(period).__name__})")

            try:
                match = re.fullmatch(r'(\d+\.\d+\.\d+)-(\d+\.\d+\.\d+)', period)
                if match:
                    st, en = str_to_datetime(match.group(1)).date(), str_to_datetime(match.group(2)).date()
                else:
                    if period not in all_periods:
                        raise ValueError(f"Период '{period}' не найден в справочнике")

                    st, en = all_periods[period].start, all_periods[period].end

                if st > en: raise ValueError(f"Неверные границы периода: {period}")
                bisect.insort_left(periods_starts, st)
                bisect.insort_left(periods_ends,   en)

            except (ValueError, KeyError, AttributeError) as ex:
                raise ValueError(f"Неверно задан период: {period} ({ex})")

            if old_count == len(periods_starts):
                raise ValueError(f"Не удалось обработать период: {period}")

        # TODO: рефактор
        all_starts = iter(periods_starts)
        all_ends = iter(periods_ends)
        cur_start = next(all_starts, None)
        cur_end   = next(all_ends,   None)
        while cur_start and cur_end:
            next_start = next(all_starts, None)
            next_end = next(all_ends, None)
            if (next_start and next_end) and (
                    next_start - cur_end).days <= 1:  # Если есть следующий промежуток, и он вплотную то объединяем
                cur_end = next_end
            else:
                self.periods_constraint_dates.append(
                    TimePeriod(cur_start, cur_end)
                )
                cur_start = next_start
                cur_end = next_end
        if cur_start and cur_end:
            self.periods_constraint_dates.append(
                TimePeriod(cur_start, cur_end)
            )

    @staticmethod
    def get_week_parity(when: date):
        return when.isocalendar().week % 2

    @staticmethod
    def _comparability_v1_to_v2(data_v1):
        def update_single(data):
            for old_name, new_name, is_list in (
                ("dayW", "dayW", True),
                ("dayM", "dayM", True),
                ("mon",  "months", True),
                ("year", "years", True),
                ("periods", "periods", True),
                ("parity", "week_parity", False)
            ):
                if old_name in data:
                    if is_list and (not isinstance(data[old_name], list)):
                        data[new_name] = [data[old_name]]
                    else:
                        data[new_name] = data[old_name]
            return data

        if isinstance(data_v1, list):
            return {
                "mixed": list(map(update_single, data_v1))
            }
        else:
            return update_single(data_v1)

    @staticmethod
    def from_json(data: dict[str, Any], version):
        # ===========================================
        # Совместимость V1 -> V2
        if version == 1:
            data = MultiDateHolder._comparability_v1_to_v2(data)
            version = 2
        # ===========================================

        time = data.get("time")
        constraints = {}
        if data.get("months"):
            constraints["month_constraint"] = data["months"]

        if data.get("years"):
            constraints["year_constraint"] = data["years"]

        if data.get("periods"):
            constraints["periods_constraint"] = data["periods"]

        if data.get("week_parity"):
            constraints["week_parity_constraint"] = data["week_parity"]

        try:
            if "mixed" in data:
                base = MultiDateMixer(
                    [MultiDateHolder.from_json(sub_data, 2) for sub_data in data["mixed"]],
                    formula=data.get("formula")
                )
            elif "dayW" in data:
                base = MultiDateWeekday(time, data["dayW"], **constraints)
            elif "dayM" in data:
                base = MultiDateMonthday(time, data["dayM"], **constraints)
            elif "anchor_date" in data:
                base = MultiDateParity(
                    time,
                    str_to_datetime(data["anchor_date"]).date(),
                    data["days_on"],
                    data["days_off"],
                    firstly_on=data["firstly_on"], **constraints
                )
            else:
                raise ValueError(f"Не удалось определить тип даты из этого JSON: {data}")
        except KeyError as ex:
            raise ValueError(f"Не удалось загрузить (отсутствует параметр {ex.args[0]}) дату из этого JSON: {data}")

        return base

    @abstractmethod
    def to_json(self) -> dict:
        """
            :return: Возвращает собственную интерпретацию в виде данных
        """
        raise NotImplementedError()

    def _with_constraints_data(self, addition: dict):
        result = {"time": self.time}
        if self.month_constraint:
            result["months"] = list(self.month_constraint)
        if self.year_constraint:
            result["years"]  = list(self.year_constraint)
        if self.periods_constraint:
            result["periods"] = self.periods_constraint
        if self.week_parity_constraint is not None:
            result["week_parity"] = self.week_parity_constraint
        result.update(addition)
        return result

    def to_str(self):
        specific_str = self._impl_to_str()
        if specific_str == "Никогда": return specific_str

        if self.month_constraint:
            specific_str += f", {tuple_range_to_str(sorted(list(self.month_constraint)), lambda mon: months[mon-1][2])}"
        if self.year_constraint:
            specific_str += f", {tuple_range_to_str(sorted(list(self.year_constraint)), lambda year: f'{year}г')}"

        return specific_str

    @abstractmethod
    def _impl_to_str(self):
        raise NotImplementedError()

    def clamp_to_constraints(self, start_date: date, end_date: date) -> Generator[tuple[date, date], None, None]:
        # TODO: рефактор
        def yield_target_range():
            yield start_date, end_date

        def all_periods_ranges():
            min_date = start_date
            for period in self.periods_constraint_dates:
                if period.start < min_date: continue
                jump_to = yield period.get_start(), period.get_end()
                if jump_to: min_date = jump_to

        def all_year_ranges():
            if not self.year_constraint: return
            cursor = date(self.year_constraint[0], 1, 1)
            for year in self.year_constraint:
                if cursor.year > year: continue
                cursor = cursor.replace(year=year, month=1, day=1)
                jump_to = yield cursor, month_end(cursor.replace(month=12))
                if jump_to: cursor = jump_to

        def all_month_ranges():
            if not self.month_constraint: return
            cursor = start_date.replace(day=1)
            try:
                while cursor < end_date:
                    while True: # Говно кодище
                        try:
                            for month in self.month_constraint:
                                if cursor > end_date: return
                                if cursor.month > month: continue
                                cursor = cursor.replace(month=month, day=1)
                                jump_to = yield cursor, month_end(cursor)
                                if jump_to:
                                    cursor = jump_to
                                    raise ArithmeticError() # Говно кодище
                            cursor = cursor.replace(year=cursor.year + 1, month=1, day=1)
                            break
                        except ArithmeticError: # Говно кодище
                            pass
            except OverflowError:
                pass

        # Выдаёт недели, чётность которых соответствует заданной, если чётность не указана ничего не выдаёт
        def all_parity_weeks_ranges():
            if self.week_parity_constraint is None: return
            cursor = start_date - timedelta(days=start_date.weekday())
            while cursor < end_date:
                if self.get_week_parity(cursor) != self.week_parity_constraint:
                    cursor += timedelta(days=7)
                jump_to = yield cursor, cursor + timedelta(days=6)
                if jump_to: cursor = jump_to - timedelta(days=jump_to.weekday())
                else: cursor += timedelta(days=7)

        # МЫ СТРОГО РАБОТАЕМ ИЗ ПРЕДПОЛОЖЕНИЯ ЧТО ВСЕ ГЕНЕРАТОРЫ ДАЮТ
        # СОРТИРОВАННЫЙ НАБОР НЕПЕРЕСЕКАЮЩИХСЯ В ПРЕДЕЛАХ ЭТОГО ГЕНЕРАТОРА
        # ПРОМЕЖУТКОВ!!! ЕСЛИ ЭТО НЕ ТАК ТО РЕЗУЛЬТАТ БУДЕТ НЕВЕРНЫМ!

        prev_start, prev_end = None, None
        valid_generators = (
                [yield_target_range()] +  # Обязателен
                ([all_parity_weeks_ranges()] if self.week_parity_constraint is not None else []) +
                ([all_month_ranges()]        if self.month_constraint else []) +
                ([all_year_ranges()]         if self.year_constraint  else []) +
                ([all_periods_ranges()]      if self.periods_constraint_dates else [])
        )
        try:
            gens: list[tuple[Generator | Iterator, tuple[date, date]]] = [
                (gen, next_value)
                for gen, next_value in [(g, next(g)) for g in valid_generators]
            ]
            while gens:
                # Если пересекаются все со всеми -> Пересекается любой с любым, в том числе и с первым
                # НО НЕ В ОБРАТКУ! Поэтому не с первым, а с минимальным (он точно со всеми пересечётся)
                first_val = gens[0][1]
                seg_start, seg_end = first_val
                for _, other_val in gens[1:]:
                    # e2 > s1 AND e1 > s2
                    if not (other_val[1] >= seg_start and seg_end >= other_val[0]):
                        # если НЕ пересекаются
                        break
                    # Обрезаем исходя из положения, что все промежутки пересекаются
                    seg_start = max(seg_start, other_val[0])
                    seg_end   = min(seg_end,   other_val[1])
                else:
                    if prev_end is None or (seg_start - prev_end).days <= 1:
                        if prev_start is None: prev_start = seg_start
                        prev_end = seg_end
                    else:
                        yield prev_start, prev_end
                        prev_start, prev_end = seg_start, seg_end
                    # Пихаем генератор с наименьшим концом
                    i = min(range(len(gens)), key=lambda i: gens[i][1][1])
                    next_value = next(gens[i][0])
                    gens[i] = (gens[i][0], next_value)
                    continue

                # Если не ок, то пихаем генераторы так, чтобы они могли пересекаться
                # (т.е. пихаем те, у которых конец периода не достаёт до начала max периода
                # При возникновении StopIteration или промежутка за обозреваемыми границами завершаем вычисление
                max_gen, max_value = max(gens, key=lambda entry: entry[1][0])
                # Тут обязательно list-comprehensions вместо генераторного выражения, ведь в генераторном
                # выражении при вызове StopIteration от генератора, заставит его заплакать и преобразовать его
                # в RuntimeError, что нам нахер не надо
                gens = [
                    (gen, next_value)
                    for gen, next_value in (
                        [(gen2, (gen2.send(max_value[0]) if val2[1] < max_value[0] else val2)) for gen2, val2 in gens]
                    )
                ]
        except StopIteration: pass

        if prev_start and prev_end:
            yield prev_start, prev_end

    def does_match_constraints(self, when_date: date):
        if self.year_constraint and when_date.year not in self.year_constraint:
            return False

        if self.month_constraint and when_date.month not in self.month_constraint:
            return False

        for period in self.periods_constraint_dates:  # Все периоды через ИЛИ
            if period.start <= when_date <= period.end:
                break
        else:
            if self.periods_constraint_dates:
                return False

        if self.week_parity_constraint is not None:
            if self.get_week_parity(when_date) != self.week_parity_constraint:
                return False

        return True

    def is_happening(self, when_date: date) -> bool:
        if not self.does_match_constraints(when_date): return False
        return self._impl_is_happening(when_date)

    @abstractmethod
    def _impl_is_happening(self, when_date: date) -> bool:
        """
            :return: Возвращает True, если событие происходит в when_date,
        """
        raise NotImplementedError()

    def get_all_timestamps(self, start_date: date, end_date: date) -> Iterator[EventStamp]:
        if start_date > end_date: return
        for period in self.periods_constraint_dates:
            if not (start_date > period.end or end_date < period.start):
                break
        else:
            if self.periods_constraint_dates:
                return

        if start_date == end_date and self.does_match_constraints(start_date):
            yield from self._impl_get_all_timestamps(start_date, start_date)
        else:
            for start_period, end_period in self.clamp_to_constraints(start_date, end_date):
                yield from self._impl_get_all_timestamps(start_period, end_period)
            # for stamp in self._impl_get_all_timestamps(start_date, end_date):
            #     if self.does_match_constraints(stamp.get_date()):
            #         yield stamp

    @abstractmethod
    def _impl_get_all_timestamps(self, start_date: date, end_date: date) -> Iterator[EventStamp]:
        """
            :return: Генератор, который выдаёт СОРТИРОВАННЫЙ ПО ВОЗРАСТАНИЮ список
            дат + времени, когда это событие будет происходить
        """
        raise NotImplementedError()

    def count_timestamps(self, start_date: date, end_date: date) -> int:
        total = 0
        for start_period, end_period in self.clamp_to_constraints(start_date, end_date):
            total += self._impl_count_timestamps(start_period, end_period)
        return total

    @abstractmethod
    def _impl_count_timestamps(self, start_date: date, end_date: date) -> int:
        """
            :return: Выдаёт кол-во раз (кол-во дней) когда событие произойдёт в
            заданный промежуток времени
        """
        raise NotImplementedError()

    def get_next_timestamp(self, when_date: date) -> Optional[EventStamp]:
        """
            :return: Ровно 1 дату, когда произойдёт это событие.
            Дата максимально близко к when_date, но не раньше (может совпадать)
        """
        return next(self.get_all_timestamps(when_date, date(9999, 1, 1)), None)


def constraint_range(holder: MultiDateHolder, st_date: date, en_date: date):
    return tuple_range_to_ranges([
        st_date + timedelta(days=day_i)
        for day_i in range((en_date - st_date).days + 1)
        if holder.does_match_constraints(st_date + timedelta(days=day_i))
    ], comparator=lambda a, b: (b - a).days <= 1)


class MultiDateEmpty(MultiDateHolder):
    def __init__(self, **constraints):
        super().__init__([0, 0], **constraints)

    def to_json(self) -> dict:
        return self._with_constraints_data({})

    def _impl_to_str(self):
        return "Никогда"

    def _impl_is_happening(self, when_date: date) -> bool:
        return False

    def _impl_get_all_timestamps(self, start_date: date, end_date: date) -> Iterator[EventStamp]:
        raise StopIteration()

    def _impl_count_timestamps(self, start_date: date, end_date: date) -> int:
        return 0


if __name__ == '__main__':
    h = MultiDateEmpty(
        year_constraint=[2026],
        month_constraint=[1, 2, 3],
        periods_constraint=["08.02.2024-15.02.2026"],
        week_parity_constraint=1
    )
    print(*list(h.clamp_to_constraints(date(1, 1, 1), date(9999, 12, 31))), sep="\n")
    exit()


class MultiDateWeekday(MultiDateHolder):
    def __init__(self, time, weekdays: list[int], **constraints):
        super().__init__(time, **constraints)
        for weekday in weekdays: assert 1 <= weekday <= 7, "День недели должен быть от 1 до 7"
        self._weekdays = tuple(sorted(set(weekdays)))

    def _impl_to_str(self):
        if not self._weekdays: return "Никогда"
        return tuple_range_to_str(self._weekdays, lambda index: days_of_week[index - 1])

    def to_json(self) -> dict:
        return super()._with_constraints_data({
            "dayW": self._weekdays
        })

    def _impl_is_happening(self, when_date: date):
        return when_date.isoweekday() in self._weekdays

    def _impl_get_all_timestamps(self, start_date: date, end_date: date):
        week_start = start_date + timedelta(days=-start_date.weekday())
        weeks_count = ((end_date - week_start).days - end_date.weekday()) // 7 + 1

        for _ in range(weeks_count):
            for weekday in self._weekdays:
                day = week_start + timedelta(days=weekday-1)
                if day < start_date: continue
                if day > end_date: break
                yield EventStamp(day, self.time)
            week_start += timedelta(days=7)

    def _impl_count_timestamps(self, start_date: date, end_date: date):
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
    def __init__(self, time, monthdays: list[int], **constraints):
        super().__init__(time, **constraints)
        for monthday in monthdays: assert 1 <= monthday <= 31, "День месяца должен быть от 1 до 31"
        self._monthdays = tuple(sorted(set(monthdays)))

    def _impl_to_str(self):
        if not self._monthdays: return "Никогда"
        return f"{tuple_range_to_str(self._monthdays)} {'число' if len(self._monthdays) < 2 else 'числа'}"

    def to_json(self) -> dict:
        return super()._with_constraints_data({
            "dayM": self._monthdays
        })

    def _impl_is_happening(self, when_date: date):
        return when_date.day in self._monthdays

    def _impl_get_all_timestamps(self, start_date: date, end_date: date):
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
            yield EventStamp(cursor, self.time)
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

    def _impl_count_timestamps(self, start_date: date, end_date: date) -> int:
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
    def __init__(self, time, anchor: date, days_on: int, days_off: int, firstly_on=True, **constraints):
        super().__init__(time, **constraints)
        self.anchor     = anchor
        self.days_on    = days_on
        self.days_off   = days_off
        self.firstly_on = firstly_on

    def _impl_to_str(self):
        if self.anchor is None: return "Никогда"
        if self.days_on * self.days_off == 0: return "Никогда"
        return f"С {self.anchor.day} {months[self.anchor.month-1][0]} {self.anchor.year}, " + \
              (f"{word_case(self.days_on, 'день', 'дня', 'дней')} через {self.days_off}"
               if self.firstly_on else
               f"через {word_case(self.days_off, 'день', 'дня', 'дней')} по {self.days_off}")

    def to_json(self) -> dict:
        return super()._with_constraints_data({
            "anchor_date": datetime_to_str(self.anchor),
            "days_on":  self.days_on,
            "days_off": self.days_off,
            "firstly_on": self.firstly_on
        })

    def _impl_is_happening(self, when_date: date) -> bool:
        raise NotImplementedError()

    def _impl_get_all_timestamps(self, start_date: date, end_date: date):
        full_loop = self.days_on + self.days_off
        if full_loop <= 0: return

        if self.firstly_on:
            anchor, days_on, days_off = self.anchor, self.days_on, self.days_off
        else:
            anchor = self.anchor - timedelta(days=self.days_off)
            days_on, days_off = self.days_off, self.days_on

        days_passed = (anchor - start_date).days
        closest_anchor = anchor
        if days_passed < 0:
            closest_anchor += timedelta(days=(-days_passed // full_loop) * full_loop)
        else:
            closest_anchor -= timedelta(days=ceil(days_passed / full_loop)) * full_loop
            # Сдвинуть максимально якорь на full_loop * X, чтобы было до start_date и X был наименьшим

        i = 0
        for _ in range((end_date - closest_anchor).days // full_loop + 1):
            for delta in range(days_on):
                date = closest_anchor + timedelta(days=i)
                i += 1
                if date < start_date: continue
                if date > end_date: return
                yield EventStamp(date, self.time)
            i += days_off

    def _impl_count_timestamps(self, start_date: date, end_date: date) -> int:
        count = 0
        full_loop = self.days_on + self.days_off

        if self.firstly_on:
            anchor, days_on, days_off = self.anchor, self.days_on, self.days_off
        else:
            anchor = self.anchor - timedelta(days=self.days_off)
            days_on, days_off = self.days_off, self.days_on

        days_passed = (start_date - anchor).days

        middle_anchor = anchor + timedelta(ceil(days_passed / full_loop) * full_loop)
        full_loops_fit = ((end_date - middle_anchor).days + 1) // full_loop
        count += full_loops_fit * days_on

        # Смотрим на края вошедшего диапазона
        left_loop_size = (middle_anchor - start_date).days
        count += max(0, left_loop_size - days_off)

        right_loop_size = (end_date - middle_anchor).days + 1 - full_loops_fit * full_loop
        count += min(right_loop_size, days_on)

        return count


class AllTimestampsWrapper:
    def __init__(self, holder: MultiDateHolder, st_date: date, en_date: date):
        self.generator = holder.get_all_timestamps(st_date, en_date)

    def __eq__(self, other):
        raise TypeError()

    def __mul__(self, other):  # and -> *
        if not isinstance(other, AllTimestampsWrapper): raise TypeError()
        return mix_gen_and(self.generator, other.generator)

    def __add__(self, other):  # or -> +
        if not isinstance(other, AllTimestampsWrapper): raise TypeError()
        return mix_gen_or(self.generator, other.generator)


def mix_gen_or(gen1: Iterator | list, gen2: Iterator | list):
    """
        ПРЕДПОЛАГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАННОМ ВИДЕ
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


def mix_gen_and(gen1: Iterator | list, gen2: Iterator | list):
    """
        ПРЕДПОЛАГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАННОМ ВИДЕ
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


def mix_gen_or_multi(*gens: Iterator | list):
    """
        ПРЕДПОЛАГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАННОМ ВИДЕ
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
            if (elems[i] is not None) and (elems[i] == min_val):
                elems[i] = next(iters[i], None)


def mix_gen_and_multi(*gens: Iterator | list):
    """
        ПРЕДПОЛАГАЕТСЯ ЧТО ГЕНЕРАТОРЫ ВЫДАЮТ ДАТЫ В ОТСОРТИРОВАННОМ ВИДЕ
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
    def __init__(self, holders: Iterable[MultiDateHolder] | MultiDateHolder, formula: str | None = None):
        super().__init__([0, 0])
        self.holders = tuple(holders) if isinstance(holders, Iterable) else (holders,)
        # Если формула None, то все объекты будут объединены (т.е. A + B + C ... + Z)
        self.formula = formula

    def _impl_to_str(self):
        return "Миксер событий"

    def to_json(self) -> dict:
        result = {
            "mixed": [holder.to_json() for holder in self.holders],
        }
        if self.formula:
            # noinspection PyTypeChecker
            result["formula"] = self.formula

        return result

    def _get_timestamps_iterator(self, start_date: date, end_date: date):
        return (holder._impl_get_all_timestamps(start_date, end_date) for holder in self.holders)

    def _impl_is_happening(self, when_date: date) -> bool:
        return all(holder._impl_is_happening(when_date) for holder in self.holders)

    def _impl_count_timestamps(self, start_date: date, end_date: date) -> int:
        if len(self.holders) == 1:
            return self.holders[0]._impl_count_timestamps(start_date, end_date)
        return len(tuple(self._impl_get_all_timestamps(start_date, end_date)))

    @staticmethod
    def normalise_formula(formula):
        formula = formula.lower()\
            .replace("and", "*")\
            .replace("or", "+")\
            .replace("или", "+").replace("и", "*")

        for i in range(-1, 10):
            formula = formula.replace(chr(ord("б") + i), chr(ord("b") + i))
        return formula

    def _impl_get_all_timestamps(self, start_date: date, end_date: date) -> Iterator[EventStamp]:
        if len(self.holders) == 1:
            yield from self.holders[0]._impl_get_all_timestamps(start_date, end_date)
        elif self.formula is None:
            # Тут нельзя использовать _impl_get_all_timestamps из-за миксера
            yield from mix_gen_or_multi(*(holder.get_all_timestamps(start_date, end_date) for holder in self.holders))
        else:
            variables = {
                chr(ord("a") + i): AllTimestampsWrapper(holder, start_date, end_date)
                for i, holder in enumerate(self.holders)
            }
            yield from eval(self.normalise_formula(self.formula), variables)

    def display_calendar(self, anchor_date=datetime.now().date(), week_range_before=2, week_range_after=2):
        en_date = anchor_date + timedelta(days=-anchor_date.weekday() + 7 * week_range_after + 6)
        st_date = anchor_date - timedelta(days=+anchor_date.weekday() + 7 * week_range_before)

        # noinspection PyTypeChecker
        target_dates = set(map(EventStamp.get_date, self._impl_get_all_timestamps(st_date, en_date)))

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


if __name__ == '__main__':
    mixer = MultiDateMixer(
        [
            MultiDateParity([0,0], date(2025, 8, 28), 3, 2),
            MultiDateWeekday([0,0], [1, 2, 3, 4, 5])
        ], formula="A and B"
    )

    mixer.display_calendar(week_range_after=7)