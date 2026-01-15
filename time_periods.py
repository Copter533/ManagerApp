from datetime import datetime, date


class TimePeriod:
    def __init__(self, start: date, end: date, row = 1):
        self.start = start
        self.end   = end
        self.row = row # Для отображения

    def __repr__(self):
        return f'({self.start.strftime("%d.%m.%Y")} - {self.end.strftime("%d.%m.%Y")})'

    def match(self, check: datetime):
        return self.start <= check <= self.end

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

    def get_start(self): return self.start
    def get_end(self):   return self.end

    def __eq__(self, other):
        if not isinstance(other, TimePeriod): return False
        return self.start == other.start and self.end == other.end


all_periods = {
    'Семестр 1':     TimePeriod(date(2024, 9, 1), date(2024, 12, 29), row=1),
    'Сессия 1':      TimePeriod(date(2025, 1, 1), date(2025,  1, 31), row=2),
    'Семестр 2':     TimePeriod(date(2025, 2, 4), date(2025,  5, 31), row=1),
    'Сессия 2':      TimePeriod(date(2025, 6, 1), date(2025,  7, 30), row=2),
    'Семестр 2 (2)': TimePeriod(date(2025, 2, 4), date(2025,  5, 31), row=1),
    # 'Сессия 2 (2)':  TimePeriod(datetime(2025, 6, 1), datetime(2025,  7, 30), row=2),
}