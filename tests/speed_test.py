from datetime import datetime, date, timedelta
import os

from date_utils import Config
from multidate_v2 import MultiDateMixer
from utils import DebugTimer

os.chdir("../")

cfg = Config.load()
events = [event for event in cfg.events]

now = datetime.now().date()
print([event.name for event in events])
print(len(events))

print("Событий миксеров:")
print(len([event for event in events if isinstance(event.multi_date, MultiDateMixer)]))

# event = events[3]
# with DebugTimer(f"Время для события {event.name}"):
#     for i in range(10):
#         m: MultiDateMixer = event.multi_date
#         end_date = next(m.holders[0].clamp_to_constraints(now, date(9999, 1, 1)), None)
# print(event.name)
# print(end_date)
# exit()

with DebugTimer("Вычисление дат"):
    for i in range(1):
        for event in events:
            pass
            # # # Тесты всех событий
            # 1.73s
            stamp = event.get_next_timestamp(now - timedelta(days=1000))
            # if stamp: print(stamp)
            # 1.64 (так же)
            # next(event.get_final_timestamps(now, date(9999, 12, 31)), None)
            # 4 секунды!
            # event.multi_date.get_next_timestamp(now)

            # # # Тесты бесконечных событий (times == 0)
            # 1.52s
            # event.get_next_timestamp(now)
            # 1.59 (так же)
            # next(event.get_final_timestamps(now, date(9999, 12, 31)), None)
            # 1.53 сек
            # event.multi_date.get_next_timestamp(now)

            # 0.24 !
            # if isinstance(event.multi_date, MultiDateMixer):
            #     event.multi_date.holders[0].get_next_timestamp(now)

            # 0.63 !
            # if isinstance(event.multi_date, MultiDateMixer):
            #     for holder in event.multi_date.holders:
            #         holder.get_next_timestamp(now)

            # 0.00 !!!!!
            # if isinstance(event.multi_date, MultiDateMixer):
            #     for holder in event.multi_date.holders:
            #         next(holder._impl_get_all_timestamps(now, date(9999, 12, 31)), None)
            # else:
            #     next(event.multi_date._impl_get_all_timestamps(now, date(9999, 12, 31)), None)

            # 0.64 !!!!!!!!!!!!!!!!!!!!!
            # if isinstance(event.multi_date, MultiDateMixer):
            #     for holder in event.multi_date.holders:
            #         next(holder.clamp_to_constraints(now, date(9999, 12, 31)), None)
            # else:
            #     next(event.multi_date.clamp_to_constraints(now, date(9999, 12, 31)), None)