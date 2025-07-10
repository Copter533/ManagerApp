import win32con
import win32gui
from time import sleep

from utils import Config


class TargetedWindow:
    def __init__(self, display_name: str, condition=None, time=None):
        self.display_name = display_name
        self.condition = condition
        self.timeout = time
        self.time = 0

    def add_time(self, value):
        self.time = min(max(0, self.time + value), self.timeout)

    def time_left(self): return self.timeout - self.time

    def check(self, window_title):
        return False if self.condition is None else self.condition(window_title)

    def set_custom_condition(self, lambda_check):
        self.condition = lambda_check
        return self

    def set_in_condition(self, entry: str):
        self.condition = lambda s: entry in s
        return self

    def set_timer(self, time):
        self.timeout = time


def app_killer_thread(main_window, config: Config):
    return
    targeted_windows = [
        TargetedWindow("Ютуб", time=60).set_custom_condition(
            lambda s: 'YouTube' in s and not ('music', 'official', 'spy' in s.lower())
        ),
        TargetedWindow("Лаунчер", time=10).set_in_condition('Legacy Launcher'),
        TargetedWindow("Майн",    time=10).set_in_condition('Minecraft')
    ]

    while True:
        sleep(1)
        if not config.app_killer_enable: continue

        open_windows = {}
        win32gui.EnumWindows(enum_window_callback, open_windows)

        for targeted in targeted_windows:
            for hwnd, title in open_windows.items():
                if targeted.check(title): break
            else:
                # Уменьшение таймера
                targeted.add_time(-1)
                continue

            time_left = targeted.time_left()
            if time_left == 0:
                win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                main_window.tray_icon.showMessage("Иди работай", "пожалуйста...")
                print(f'Закрыто окно "{targeted.display_name}"')
            elif time_left in (5, 10, 30, 50):
                msg = f'Закрытие окна "{targeted.display_name}" через {time_left} сек'
                main_window.tray_icon.showMessage("Внимание!", msg)
                print(msg)

            # Увеличение таймера
            targeted.add_time(1)

def enum_window_callback(hwnd, open_windows):
    if win32gui.IsIconic(hwnd) or not win32gui.IsWindowVisible(hwnd): return
    window_title = win32gui.GetWindowText(hwnd)
    if not window_title: return

    open_windows[hwnd] = window_title
