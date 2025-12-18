import colorsys
import json
import os.path
import sys
import traceback
from collections.abc import Iterable
from datetime import datetime, timedelta, date
from random import uniform
from time import time

from announced_task import AnnouncedTask
from tags import TagList, Tags

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

def rgb_to_hex(rgb_color):
    return f'{rgb_color[0]:02X}{rgb_color[1]:02X}{rgb_color[2]:02X}'

def hex_to_rgb(hex_color):
    return tuple(int(hex_color.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

def str_time(minutes: int, leading_zero=False):
    h, m = divmod(int(minutes), 60)
    return f'{"0" if h < 10 and leading_zero else ""}{h}:{"0" if m < 10 else ""}{m}'

def word_case(num, for1, for2, for5, pref=None):
    if pref is None: pref = f'{num} '
    if 10 <= num <= 20: return f'{pref}{for5}'
    rem = num % 10
    if rem == 1:    return f'{pref}{for1}'
    if 1 < rem < 5: return f'{pref}{for2}'
    return f'{pref}{for5}'

def beauty_time(minutes: int):
    hour, mins = divmod(int(minutes), 60)
    days, hour = divmod(hour, 24)
    res = ""
    if days:              res += f'{word_case(days, "день",    "дня",     "дней")} '
    if hour:              res += f'{word_case(hour, "час",     "часа",    "часов")} '
    if mins and not days: res += f'{word_case(mins, "минута",  "минуты",  "минут")} '

    return res[:-1] if res else "Сейчас"

def beauty_date(day: date):
    return (f"{0 if day.day   < 10 else ''}{day.day}."
            f"{0 if day.month < 10 else ''}{day.month}."
            f"{day.year}")

def interpolate(min_, max_, val):
    if val < 0: return min_
    if val > 1: return max_
    return min_ + (max_ - min_) * val

def datetime_to_str(when: datetime):
    return f'{when.year}.{when.month}.{when.day}'

def str_to_datetime(when: str):
    return datetime(*map(int, when.split('.')))

def is_main_window(check_object: object):
    MainWindowClass = getattr(sys.modules['__main__'], 'MainWindow', None)
    return isinstance(check_object, MainWindowClass)

class DebugTimer:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.st = time()

    def __exit__(self, exc_type, exc_val, exc_tb):
        print(f'Time for "{self.name}" - {time() - self.st:.2f}s')

class DisplayModes:
    FIELD = "Поле"
    LIST  = "Список"

    _iterate = [FIELD, LIST]

    @staticmethod
    def check(val): return val in DisplayModes._iterate

    @staticmethod
    def cycle(curr, offset=1):
        i, l = DisplayModes._iterate.index(curr) + offset, len(DisplayModes._iterate)
        if i < 0: i += l
        return DisplayModes._iterate[i % l]

class TimePeriod:
    def __init__(self, from_: datetime, to: datetime, row = 1):
        self.from_ = from_
        self.to    = to

        self.row = row # Для отображения

    def match(self, check: datetime):
        return self.from_ <= check <= self.to

    @staticmethod
    def match_any(periods, check: datetime):
        for period in periods:
            if period.match(check): return True
        return False

    @staticmethod
    def match_all(periods, check: datetime):
        for period in periods:
            if not period.match(check): return False
        return True

class MultiDate: #OLD
    def __init__(self, weekday=None, monthday=None, month=None, year=None, time=None, parity=None):
        self._states = []

        if weekday is None and monthday is None and month is None and time is None and parity is None: return
        self.add_state(
            weekday  = weekday,
            monthday = monthday,
            month    = month,
            year     = year,
            time     = time,
            parity   = parity
        )

    def add_state(self, weekday=None, monthday=None, month=None, year=None, time=None, parity=None, periods=None):
        assert weekday is None or monthday is None, 'Нельзя указать и день месяца и день недели одновременно'
        assert time, 'Обязательно нужно указать время'

        for min_, max_, name, value in [
            [1,    7,    'День недели', weekday],
            [1,    31,   'День месяца', monthday],
            [1,    12,   'Месяц',       month],
            [2005, 2100, 'Год',         year]
        ]:
            if value is None: continue
            for v in (value,) if isinstance(value, int) else value:
                assert min_ <= v <= max_, f'{name} должен быть от {min_} до {max_}'

        state = {k: v for k, v in {
            "parity": parity,
            "dayW": self.check_number_plus(weekday),
            "dayM": self.check_number_plus(monthday),
            "mon":  self.check_number_plus(month),
            "year": self.check_number_plus(year),
            "time": self.time_str_to_stamp(time) if isinstance(time, str) else time,
            "periods": periods if isinstance(periods, list) else list(periods or [])
        }.items() if v is not None}

        assert tuple(state.keys()) != ('time',), 'Помимо времени нужно ещё что-то указать'
        self._states.append(state)

    def get_states(self):
        return self._states

    def check_number_plus(self, value):
        if value is None or\
            False if not isinstance(value, Iterable) else (
                (len(value) == 0) or
                (len(value) == 1 and value[0] is None)
            ):
            return None

        return tuple(set(value)) if isinstance(value, Iterable) else (value,)

    def have_time_intersects(self, other, when=datetime.now()):
        other: MultiDate
        other_stamps = other.get_timestamps(when)
        for stamp1 in self.get_timestamps(when):
            for stamp2 in other_stamps:
                if max(stamp1[0], stamp2[0]) <= min(stamp1[1], stamp2[1]):
                    return True
        return False

    @classmethod
    def from_json(cls, obj: dict):
        res = cls()
        for state in (obj if isinstance(obj, list) else [obj]):
            data = state.copy()
            res.add_state(
                parity   = data.get('parity'),
                weekday  = data.get('dayW'),
                monthday = data.get('dayM'),
                month    = data.get('mon'),
                year     = data.get('year'),
                time     = data.get('time'),
                periods  = data.get('periods')
            )
        res._states.sort(key=cls.get_sort_value_for_state)
        return res

    def to_json(self):
        res = []
        for state in self._states:
            data = state.copy()
            for k in ('dayW', 'dayM', 'mon', 'year'):
                if k not in data: continue
                if len(data[k]) == 1: data[k] = data[k][0]
            res.append({k: v for k, v in data.items() if v is not None})
        return res if len(res) > 1 else res[0]

    @staticmethod
    def time_str_to_stamp(timestr: str):
        if timestr is None: return None
        values = [tuple(map(int, time.split(":"))) for time in timestr.split("-")]
        return values[0][0] * 60 + values[0][1], values[1][0] * 60 + values[1][1]

    @staticmethod
    def time_stamp_to_str(stamp: list[int], mid="-"):
        if stamp is None: return None
        if isinstance(stamp, str): return stamp
        h1, m1 = map(int, divmod(stamp[0], 60))
        h2, m2 = map(int, divmod(stamp[1], 60))
        return f'{h1}:{"0" if m1 < 10 else ""}{m1}{mid}{h2}:{"0" if m2 < 10 else ""}{m2}'

    @staticmethod
    def match(state, target_state: dict):
        """
        Не проверяет даты отмены и кол-во выполнений
        :param state:
        :param target_state:
        :return:
        """
        if state.get('periods') and not TimePeriod.match_any(
                [all_periods[period_name] for period_name in state['periods']],
                datetime(target_state['year'], target_state['mon'], target_state['dayM'])
        ):
            return False

        for k, v in state.items():
            if v is None or k in ('time', 'periods'): continue
            if isinstance(v, int  ) and target_state[k] == v: continue
            if isinstance(v, tuple) and target_state[k] in v: continue
            return False
        return True

    def get_timestamps(self, when: dict | date) -> list[list[int]]:
        targ_state = when if isinstance(when, dict) else {
            "parity": when.isocalendar().week % 2,
            "dayW": when.isoweekday(),
            "dayM": when.day,
            "mon":  when.month,
            "year": when.year
        }
        return sorted([i['time'] for i in self._states if self.match(i, targ_state)], key=lambda x: x[0])

    def get_sort_value(self, when=None):
        return 999 if not self._states else min(
            self.get_sort_value_for_state(state, when) for state in self._states
        )

    @staticmethod
    def get_sort_value_for_state(state: dict, when=None):
        now = when or datetime.now()
        dayW = min(state['dayW']) if 'dayW' in state else min(
            [datetime(now.year, min(state['mon'] or [now.month]), day).isoweekday()
             for day in state['dayM']]
        )
        return dayW + state['time'][0] / (24 * 60)

    @staticmethod
    def tuple_range_to_str(v: tuple, replacer=None):
        if v is None: return None
        if replacer is None: replacer = lambda x: x
        if len(v) == 1: return str(replacer(v[0]))

        arr = sorted(v)
        res = [[arr[0]]]
        for i in range(1, len(v)):
            if arr[i] - arr[i-1] <= 1:
                if len(res[-1]) == 1:
                    res[-1] = [res[-1][0], arr[i]]
                else:
                    res[-1][1] = arr[i]
            else:
                res.append([arr[i]])

        return ', '.join([str(replacer(a[0])) if len(a) == 1 else f'{replacer(a[0])}-{replacer(a[1])}' for a in res])

    @staticmethod
    def str_state(state: dict):
        if not state: return 'Никогда'
        res = ""

        time   = state.get('time') or [0, 24*60]
        dayM   = MultiDate.tuple_range_to_str(state.get('dayM'))
        dayW   = MultiDate.tuple_range_to_str(state.get('dayW'),
                                              replacer=lambda x: days_of_week[x-1])
        mon     = state.get('mon')
        parity  = state.get('parity')
        periods = state.get('periods')

        if dayM and mon:
            res += f'{dayM} {MultiDate.tuple_range_to_str(mon, replacer=lambda x: months[x-1][0])}, ' # 1 апреля
        elif dayM:
            res += f'{dayM} числа, '                                                                  # 1 число
        elif mon:
            res += f'в {MultiDate.tuple_range_to_str(mon, replacer=lambda x: months[x-1][1])} '       # в апреле

        if dayW: res += f'{dayW}, '

        parity_str = ""
        if parity == 0: parity_str = ", по чётным неделям"
        if parity == 1: parity_str = ", по нечётным неделям"

        periods_str = f" во время {', '.join(periods)}" if periods else ""

        return (res or "Все дни ") + MultiDate.time_stamp_to_str(time, " - ") + parity_str + periods_str

    def __str__(self):
        if len(self._states) == 0:
            return 'Никогда'
        if len(self._states) == 1:
            return self.str_state(self._states[0])
        return 'Будет:\n'+'\n'.join(map(self.str_state, self._states))

# class MultiDateParity(MultiDate):
#     def __init__(self, anchors: list[date], on_days=0, off_days, month=None, year=None, time=None, parity=None):
#         super().__init__(None, None, month, year, time, parity)
#         self.anchors = anchors
#
#         self.on_days  = on_days
#         self.off_days = off_days
#
#     @classmethod
#     def from_json(cls, obj: dict):
#         res = cls()
#         for state in (obj if isinstance(obj, list) else [obj]):
#             data = state.copy()
#             res.add_state(
#                 parity=data.get('parity'),
#                 weekday=None,
#                 monthday=None,
#                 month=data.get('mon'),
#                 year=data.get('year'),
#                 time=data.get('time'),
#                 periods=data.get('periods')
#             )
#         res._states.sort(key=cls.get_sort_value_for_state)
#         return res
#
#     def to_json(self):
#         res = []
#         for state in self._states:
#             data = state.copy()
#             for k in ('dayW', 'dayM', 'mon', 'year'):
#                 if k not in data: continue
#                 if len(data[k]) == 1: data[k] = data[k][0]
#             res.append({k: v for k, v in data.items() if v is not None})
#         return res if len(res) > 1 else res[0]


class ScheduleEvent:
    def __init__(self, name, multi_date: MultiDate, description: str = None,
                 times=0, tags: TagList = None, anchor_date: datetime = None,
                 canceled_dates: list[date] = None, color: list[int | int | int] | str = None, tasks=None):
        self.name  = name
        self.desc  = description
        self.date  = multi_date
        self.tags  = tags or TagList()

        self.last_time_announced = None

        self.tasks: list[AnnouncedTask] = tasks or []

        self.canceled_dates = canceled_dates or []

        self.times = times
        self.anchor_date = anchor_date or datetime.now()

        self.have_color = bool(color)
        if color: self.color = hex_to_rgb(color) if isinstance(color, str) else color
        else:     self.color = [int(i * 255) for i in colorsys.hsv_to_rgb(uniform(0, 1), 0.8, 0.5)]

    @classmethod
    def from_json(cls, data: dict):
        name       = data['name']
        multi_date = MultiDate.from_json(data['date'])
        tags       = data.get('tags', {})
        desc       = data.get('desc')

        times = data.get('times', 0)
        anchor = str_to_datetime(data.get('anchor')) if 'anchor' in data else None

        tasks = [AnnouncedTask.from_file(o) for o in data.get('tasks', ())]

        cancel_dates = [date(*map(int, day.split('-'))) for day in data.get('canceled', '').split(',') if day]

        return cls(name, multi_date, times=times, description=desc, tags=TagList.from_json(tags),
                   anchor_date=anchor, canceled_dates=cancel_dates,
                   color=data.get('color'), tasks=tasks)

    def to_json(self):
        data = {
            'name': self.name,
            'date': self.date.to_json(),
            'anchor': datetime_to_str(self.anchor_date)
        }
        if self.desc:       data['desc']  = self.desc
        if self.times:      data['times'] = self.times
        if self.tags:       data['tags']  = self.tags.to_json()
        if self.have_color: data['color'] = rgb_to_hex(self.color)

        if self.tasks: data['tasks'] = [task.to_file() for task in self.tasks]

        if self.canceled_dates: data['canceled'] = ','.join(map(str, self.canceled_dates))
        return data

    def connect_app(self, app):
        for task in self.tasks:
            task.connect_app(app)

    def can_occur(self, check_date: date | datetime):
        if isinstance(check_date, datetime): check_date = check_date.date()

        if check_date in self.canceled_dates: return False
        if self.times == 0: return True
        times = self.times

        for i in range((check_date - self.anchor_date.date()).days + 1):
            iterator = self.anchor_date.date() + timedelta(i)
            if self.get_timestamps(iterator):
                if (self.times == 0 or times > 0) and iterator == check_date: return True
                times -= 1

        return False

    def can_block(self, other):
        """
            Проверяет теги двух событий, и определяет достаточно ли приоритета, чтобы
            заблокировать другое событие (оно не произойдёт, вызывать в случае наложении времени)
        """
        if other.tags.have(Tags.IMPORTANT.YES): return False
        if not self.tags.have(Tags.REPLACER.YES): return False

        if self.tags.get(Tags.LABOR) is None: return True
        return self.tags.get(Tags.LABOR) == other.tags.get(Tags.LABOR)

    # Статический словарь с событиями, которые могут произойти.
    # Первый сет - которые произойдут, второй - не произойдут
    hashed_can_happen: dict[date, tuple[set, set]] = {}
    def can_happen(self, day: date | datetime):
        if isinstance(day, datetime): day = day.date()
        if day in ScheduleEvent.hashed_can_happen:
            true_set, false_set = ScheduleEvent.hashed_can_happen[day]
            if self.name in true_set:  return True
            if self.name in false_set: return False
        else:
            ScheduleEvent.hashed_can_happen[day] = (set(), set())

        starts = self.get_next_date(day, 1, True)[0]
        if starts is None:
            ScheduleEvent.hashed_can_happen[day][1].add(self.name)
            return False
        else:
            ScheduleEvent.hashed_can_happen[day][0].add(self.name)
            return starts.date() == day

    def get_timestamps(self, when: date = datetime.now()):
        return self.date.get_timestamps(when)

    def get_sort_value(self, when=None):
        return self.date.get_sort_value(when) + self.times * 10000

    def get_next_date(self, now: [datetime | date], scope=365, merge_time=False) \
            -> tuple[datetime, datetime] | tuple[None, None]:
        if isinstance(now, date): now = datetime(now.year, now.month, now.day)

        times = self.times
        from_index = 0 if self.times == 0 else (now - self.anchor_date).days
        for i in range(-from_index, scope):
            iterator = now + timedelta(i)
            stamps = self.get_timestamps(iterator)
            if not stamps: continue

            if merge_time: stamps = [[stamps[0][0], stamps[-1][-1]]]

            if self.times != 0:
                if times == 0: return None, None
                times -= 1

            for stamp in stamps:
                h1, m1 = divmod(stamp[0], 60)
                h2, m2 = divmod(stamp[1], 60) if stamp[1] != 24 * 60 else (23, 59)
                next_date = datetime(
                    iterator.year,
                    iterator.month,
                    iterator.day,
                    h1,
                    m1
                )
                if next_date + timedelta(minutes=stamp[1] - stamp[0]) < now: continue
                return next_date, datetime(
                    iterator.year,
                    iterator.month,
                    iterator.day,
                    h2,
                    m2
                )
        return None, None

    def exec_announced(self, now=datetime.now(), scope=365):
        if not self.tasks: return

        next_date, _ = self.get_next_date(now, scope, merge_time=True)
        if next_date is None: return

        executed_minutes = None
        for task in sorted(self.tasks, reverse=True):
            ann_time = next_date - timedelta(minutes=task.delay)
            if self.last_time_announced is not None and ann_time <= self.last_time_announced:
                continue

            if executed_minutes is not None and task.delay < executed_minutes:
                break

            elif now >= ann_time:
                executed_minutes = task.delay
                task.run()

        if executed_minutes is None: return
        self.last_time_announced = next_date - timedelta(minutes=executed_minutes)


    def __eq__(self, other):
        return self.name == other.name if isinstance(other, ScheduleEvent) else self.name == other

    def __str__(self):
        return f'Событие "{self.name}" ({self.date})'

class Config:
    def __init__(self, obj: dict, file, events):
        self.file   = file
        self.events = events

        self.y_view     = obj.get('y_view')     or 0
        self.view_scale = obj.get('view_scale') or 2600

        self.asleeps = obj.get('asleeps') or {}

        self.upcoming_hidden = obj.get('upcoming_hidden') or False

        self.disp_mode       = obj.get('disp_mode') or DisplayModes.FIELD
        if not DisplayModes.check(self.disp_mode): self.disp_mode = DisplayModes.FIELD

        self.app_killer_enable = True

    @classmethod
    def load(cls, file="schedule.json"):
        try:
            assert os.path.exists(file), 'Файла с настройками не существует'
            with open(file, "r", encoding="utf-8") as f:
                d = json.load(f)

            return cls(
                d,
                file,
                tuple(map(ScheduleEvent.from_json, d.get('events', [])))
            )

        except AssertionError as ex:
            print("Ошибка при загрузки сэйва -", ex)
            if not os.path.exists(file):
                print("Создаём новый файл с настройками...")
                with open(file, "w", encoding="utf-8") as f:
                    f.write('{}')

            return cls({}, file, [])

    def save(self, events=None, y_view=None, view_scale=None, asleeps=None, upcoming_hidden=None,
                disp_mode=None,
             pretty=True, to_file=True):
        if events          is not None: self.events          = events
        if y_view          is not None: self.y_view          = y_view
        if view_scale      is not None: self.view_scale      = view_scale
        if asleeps         is not None: self.asleeps         = asleeps
        if upcoming_hidden is not None: self.upcoming_hidden = upcoming_hidden
        if disp_mode       is not None: self.disp_mode       = disp_mode

        if not to_file: return

        data = {
            'events': [], # Заполняется ниже

            'y_view':     self.y_view,
            'view_scale': self.view_scale,
            'asleeps':    self.asleeps,

            'upcoming_hidden': self.upcoming_hidden,
            'disp_mode':       self.disp_mode
        }
        for event in self.events: data['events'].append(event.to_json())

        with open(self.file, "w", encoding="utf-8") as f:
            if pretty:
                json.dump(data, f, ensure_ascii=False, indent=4)
            else:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))


def get_events_str(events):
    res = ""
    if not events: return "Нет сохранённых событий"
    for event in events:
        res += f'Событие "{event.name}":\n'
        for state in event.date.get_states():
            res += f' - {event.date.str_state(state)}\n'
        res += '\n'
    return res

def log_error():
    if not os.path.exists("error_logs"): os.mkdir("error_logs")

    now = datetime.now()
    with open(f'error_logs/{now.date()} {now.hour}-'
              f'{"0" if now.minute < 10 else ""}{now.minute}-'
              f'{"0" if now.second < 10 else ""}{now.second}.txt',
              "w", encoding="utf-8") as f:

        exc_type, exc_value, exc_traceback = sys.exc_info()
        __local_vars: dict = exc_traceback.tb_frame.f_locals

        f.write(f"TYPE    : {exc_type.__name__}\n")
        f.write(f"MESSAGE : {exc_value}\n")
        f.write("VALUES:\n")
        __variables: dict = __local_vars.copy()
        for __var_name, __value in __variables.items():
            if __var_name.startswith('__'): continue
            f.write(f" - {__var_name:>15} : {__value}\n")

        f.write("\n\n\n")
        traceback.print_tb(exc_traceback, file=f)

all_periods = {
    'Семестр 1':     TimePeriod(datetime(2024, 9, 1), datetime(2024, 12, 29), row=1),
    'Сессия 1':      TimePeriod(datetime(2025, 1, 1), datetime(2025,  1, 31), row=2),
    'Семестр 2':     TimePeriod(datetime(2025, 2, 4), datetime(2025,  5, 31), row=1),
    'Сессия 2':      TimePeriod(datetime(2025, 6, 1), datetime(2025,  7, 30), row=2),
    'Семестр 2 (2)': TimePeriod(datetime(2025, 2, 4), datetime(2025,  5, 31), row=1),
    # 'Сессия 2 (2)':  TimePeriod(datetime(2025, 6, 1), datetime(2025,  7, 30), row=2),
}

if __name__ == '__main__':
    cfg = Config.load()
    print(get_events_str(cfg.events))
