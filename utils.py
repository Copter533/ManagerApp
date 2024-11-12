import colorsys
import json
import os.path
from collections.abc import Iterable
from datetime import datetime, timedelta, date
from random import uniform

from tags import TagList

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

def word_case(num, for1, for2, for5, pref=None):
    if pref is None: pref = f'{num} '
    if 10 <= num <= 20: return f'{pref}{for5}'
    rem = num % 10
    if rem == 1:    return f'{pref}{for1}'
    if 1 < rem < 5: return f'{pref}{for2}'
    return f'{pref}{for5}'

def beauty_time(time):
    hour, mins = divmod(time, 60)
    res = ""
    if hour: res += f'{word_case(hour, "час",     "часа",    "часов")} '
    if mins: res += f'{word_case(mins, "минута",  "минуты",  "минут")} '

    return res[:-1] if res else "0 минут"

def interpolate(min_, max_, val):
    if val < 0: return min_
    if val > 1: return max_
    return min_ + (max_ - min_) * val

def datetime_to_str(when: datetime):
    return f'{when.year}.{when.month}.{when.day}'

def str_to_datetime(when: str):
    return datetime(*map(int, when.split('.')))


class MultiDate:
    def __init__(self, weekday=None, monthday=None, month=None, time=None, parity=None):
        self._states = []

        if weekday is None and monthday is None and month is None and time is None and parity is None: return
        self.add_state(
            weekday  = weekday,
            monthday = monthday,
            month    = month,
            time     = time,
            parity   = parity
        )

    def add_state(self, weekday=None, monthday=None, month=None, time=None, parity=None):
        assert weekday is None or monthday is None, 'Нельзя указать и день месяца и день недели одновременно'
        assert time, 'Обязательно нужно указать время'

        for min_, max_, name, value in [
            [1,  7, 'День недели', weekday],
            [1, 31, 'День месяца', monthday],
            [1, 12, 'Месяц',       month]
        ]:
            if value is None: continue
            for v in (value,) if isinstance(value, int) else value:
                assert min_ <= v <= max_, f'{name} должен быть от {min_} до {max_}'

        state = {k: v for k, v in {
            "parity": parity,
            "dayW": self.check_number_plus(weekday),
            "dayM": self.check_number_plus(monthday),
            "mon":  self.check_number_plus(month),
            "time": self.time_str_to_stamp(time) if isinstance(time, str) else time
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
                time     = data.get('time')
            )
        return res

    def to_json(self):
        res = []
        for state in self._states:
            data = state.copy()
            for k in ('dayW', 'dayM', 'mon'):
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
        h1, m1 = map(int, divmod(stamp[0], 60))
        h2, m2 = map(int, divmod(stamp[1], 60))
        return f'{h1}:{"0" if m1 < 10 else ""}{m1}{mid}{h2}:{"0" if m2 < 10 else ""}{m2}'

    @staticmethod
    def match(state, target_state: dict):
        for k, v in state.items():
            if v is None or k == 'time': continue
            if isinstance(v, int  ) and target_state[k] == v: continue
            if isinstance(v, tuple) and target_state[k] in v: continue
            return False
        return True

    def get_timestamps(self, targ_state):
        return [i for i in self._states if self.match(i, targ_state)]

    def get_sort_value(self):
        now = datetime.now()
        minimum = 999 # Макс 8
        for state in self._states:
            dayW = min(state['dayW']) if 'dayW' in state else min(
                [datetime(now.year, min(state['mon'] or [now.month]), day).isoweekday()
                 for day in state['dayM']]
            )
            minimum = min(minimum,
                dayW + state['time'][0] / (24*60)
            )
        return minimum

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
        mon    = state.get('mon')
        parity = state.get('parity')

        if dayM and mon:
            res += f'{dayM} {MultiDate.tuple_range_to_str(mon, replacer=lambda x: months[x-1][0])}, ' # 1 апреля
        elif dayM:
            res += f'{dayM} числа, '                           # 1 число
        elif mon:
            res += f'в {MultiDate.tuple_range_to_str(mon, replacer=lambda x: months[x-1][2])}'        # в апреле

        if dayW: res += f'{dayW}, '

        parity_str = ""
        if parity == 0: parity_str = ", по чётным неделям"
        if parity == 1: parity_str = ", по нечётным неделям"

        return res + MultiDate.time_stamp_to_str(time, " - ") + parity_str

    def __str__(self):
        if len(self._states) == 0:
            return 'Никогда'
        if len(self._states) == 1:
            return self.str_state(self._states[0])
        return 'Будет:\n'+'\n'.join(map(self.str_state, self._states))


class ScheduleEvent:
    def __init__(self, name, multi_date: MultiDate, times=0, tags: TagList = None, anchor_date: datetime = None,
                 canceled_dates: list[date] = None, color: list[int | int | int] | str = None):
        self.name  = name
        self.date  = multi_date
        self.tags  = tags or TagList()

        self.canceled_dates = canceled_dates or []

        self.times = times
        self.anchor_date = anchor_date or datetime.now()

        self.have_color = bool(color)
        if color: self.color = hex_to_rgb(color) if isinstance(color, str) else color
        else:     self.color = [int(i * 255) for i in colorsys.hsv_to_rgb(uniform(0, 1), 0.8, 0.5)]

    def __eq__(self, other):
        return self.name == other.name if isinstance(other, ScheduleEvent) else self.name == other

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

    @classmethod
    def from_json(cls, data: dict):
        name       = data['name']
        multi_date = MultiDate.from_json(data['date'])
        tags       = data.get('tags', {})

        times = data.get('times', 0)
        anchor = str_to_datetime(data.get('anchor')) if 'anchor' in data else None

        cancel_dates = [date(*map(int, day.split('-'))) for day in data.get('canceled', '').split(',') if day]

        return cls(name, multi_date, times, tags=TagList.from_json(tags),
                   anchor_date=anchor, canceled_dates=cancel_dates,
                   color=data.get('color'))

    def to_json(self):
        data = {
            'name': self.name,
            'date': self.date.to_json(),
            'anchor': datetime_to_str(self.anchor_date)
        }
        if self.times:      data['times'] = self.times
        if self.tags:       data['tags']  = self.tags.to_json()
        if self.have_color: data['color'] = rgb_to_hex(self.color)

        if self.canceled_dates: data['canceled'] = ','.join(map(str, self.canceled_dates))
        return data

    def get_timestamps(self, when: date = datetime.now()):
        return self.date.get_timestamps({
            "parity": when.isocalendar().week % 2,
            "dayW": when.isoweekday(),
            "dayM": when.day,
            "mon":  when.month
        })

    def __str__(self):
        return f'Событие "{self.name}" ({self.date})'


class Config:
    def __init__(self, obj: dict, file, events):
        self.file   = file
        self.events = events
        self.y_view     = obj.get('y_view',   ) or 0
        self.view_scale = obj.get('view_scale') or 2600

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

    def save(self, events=None, y_view=None, view_scale=None, pretty=False):
        if events:     self.events     = events
        if y_view:     self.y_view     = y_view
        if view_scale: self.view_scale = view_scale

        data = {
            'events': [],
            'y_view': y_view,
            'view_scale': view_scale
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

if __name__ == '__main__':
    cfg = Config.load()
    print(get_events_str(cfg.events))
