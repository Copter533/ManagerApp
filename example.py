from utils import ScheduleEvent, save_schedule, MultiDate, load_schedule, get_events_str

old_schedule = {"events":[{"name":"Инфа","date":[{"parity":0,"dayW":1,"time":[700,790]},{"parity":0,"dayW":1,"time":[810,900]}],"anchor":"2024.11.11","tags":{},"color":"BF2DE7"},{"name":"English","date":[{"dayW":5,"time":[920,1010]},{"dayW":5,"time":[1020,1110]}],"anchor":"2024.11.11","tags":{"WHERE":"LOMO"},"color":"6E0D2C"},{"name":"История","date":[{"parity":0,"dayW":4,"time":[700,790]},{"parity":0,"dayW":4,"time":[810,900]}],"anchor":"2024.11.11","tags":{"WHERE":"CRON"},"color":"CD6A00"},{"name":"МатАн","date":[{"dayW":5,"time":[700,790]},{"dayW":5,"time":[810,900]}],"anchor":"2024.11.11","tags":{"WHERE":"LOMO"},"color":"D22828"},{"name":"ОПД","date":{"parity":1,"dayW":3,"time":[600,690]},"anchor":"2024.11.11","tags":{"WHERE":"LOMO"},"color":"273E4C"},{"name":"Физра","date":{"dayW":7,"time":[540,720]},"anchor":"2024.11.11","tags":{"WHERE":"SPORT","LABOR":"SPORT"},"color":"05A100"},{"name":"ОПД сдавайся","date":[{"parity":0,"dayW":3,"time":[700,790]},{"parity":0,"dayW":3,"time":[810,900]}],"anchor":"2024.11.11","tags":{"WHERE":"CRON"},"color":"563B76"},{"name":"Прога","date":[{"parity":0,"dayW":6,"time":[810,900]},{"parity":0,"dayW":6,"time":[920,1010]}],"anchor":"2024.11.11","tags":{"WHERE":"CRON"},"color":"02BBB2"},{"name":"Коллок Мат.Ан. 1122","date":{"dayM":14,"mon":11,"time":[960,1050]},"anchor":"2024.11.11","times":1,"tags":{"WHERE":"LOMO","IMPORTANT":"YES"},"color":"73138E"},{"name":"English REPL","date":{"dayW":3,"mon":11,"time":[920,1010]},"anchor":"2024.11.12","times":1,"tags":{"WHERE":"LOMO"},"color":"600B0D"},{"name":"Диско дед","date":[{"dayW":2,"time":[1020,1110]},{"dayW":2,"time":[1120,1210]}],"anchor":"2024.11.11","tags":{"WHERE":"CRON"},"color":"FFD310"},{"name":"💀 Пара в 8:20💀","date":{"dayW":3,"time":[500,590]},"anchor":"2024.11.11","tags":{"WHERE":"LOMO","LABOR":"REST"},"color":"4C0000"},{"name":"Линал","date":[{"dayW":2,"time":[700,790]},{"dayW":2,"time":[810,900]}],"anchor":"2024.11.11","tags":{"WHERE":"LOMO"},"color":"0E91C9"}]}

# inf_date = MultiDate()
# inf_date.add_state(weekday=[1, 5], time="11:40-13:10", parity=0)
# inf_date.add_state(weekday=1, time="13:30-15:00", parity=0)
#
# save_schedule([
#     ScheduleEvent("Инфа",  inf_date, color="#ff00ff"),
#     ScheduleEvent("Физра", MultiDate(weekday=7, time="9:00-12:00"), color="#00ff00")
# ])

# Проверка
events = load_schedule()
print(get_events_str(events))
save_schedule(events, pretty=True)