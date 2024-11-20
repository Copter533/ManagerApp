import sys

import pyautogui as pgui

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout, QPushButton, QMenu, QMainWindow, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer

from gui_additions import simple_label, simple_button, icon_button


class ClickerAction:
    title: str
    delay = 0

    def __init__(self, clicker, delay=None):
        self.clicker: AutoClickerGui = clicker
        if delay: self.delay = delay

    def get_title(self):
        return self.title

    def run(self): raise NotImplemented


class SendNotification(ClickerAction):
    title = "Отправка сообщения"

    def __init__(self, clicker, message, **kwargs):
        super().__init__(clicker, **kwargs)
        self.msg = message

    def run(self):
        print("Сообщение:", self.msg)


class PressHotKey(ClickerAction):
    delay = .5
    

    def get_title(self):
        return " + ".join(self.hotkey)

    def __init__(self, clicker, hotkey: str, **kwargs):
        super().__init__(clicker, **kwargs)
        self.hotkey = [
            i.lower() if len(i) == 1 and i.isalpha() else i
            for i in hotkey.split("+")]

    def run(self):
        pgui.hotkey(*self.hotkey, interval=.1)


class AutoClickerGui(QFrame):
    def __init__(self):
        super().__init__()

        # Настройка окна
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Для исключения из панели задач
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Прозрачный фон

        self.frame = QFrame()
        self.frame.setMinimumWidth(600)
        self.frame.setFixedHeight(55) # af4151
        self.frame.setObjectName("mainFrame")
        self.frame.setStyleSheet("""
            #mainFrame {
                background-color: #F91200; border: 5px solid black;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """)

        self.status_label = simple_label("", 15)
        self.stop_button  = icon_button("remove.svg", 30, 35, 'red',
                                        callback=self.set_canceled)

        self.min_pos = -60
        self.max_pos = -5

        self.finished = False
        self.base_pos = self.min_pos - 10
        self.y_set_delay = 0

        content_layout = QHBoxLayout()
        content_layout.addWidget(self.status_label)
        content_layout.addWidget(self.stop_button)
        self.frame.setLayout(content_layout)

        layout = QVBoxLayout()
        layout.addWidget(self.frame)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        self.fade_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.fade_timer.timeout.connect(self.set_y_pos)
        self.fade_timer.start(10)

        self.set_y_pos()

        self.execute_timer = QTimer(self)

        self.action_index = 0
        self.actions: list[ClickerAction] = [
            PressHotKey(self, "Win+D"),
            PressHotKey(self, "Win+1"),
            PressHotKey(self, "Alt+F4"),
            PressHotKey(self, "Win+5",  delay=1),
        ]

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.execute_loop()

    def resizeEvent(self, a0):
        w = QGuiApplication.primaryScreen().size().width()
        self.move((w - self.width()) // 2, self.y())

    def set_y_pos(self):
        if self.y_set_delay > 0:
            self.y_set_delay -= 1
            return

        target = self.min_pos if self.finished else self.max_pos
        self.base_pos += (target - self.base_pos) / 10
        self.move(self.x(), int(self.base_pos))

    def add_action(self, action):
        self.actions.append(action)

    def stop(self):
        self.execute_timer.stop()
        self.close()
        exit(0)

    def set_started(self):
        self.finished = False
        self.frame.setStyleSheet("""
            #mainFrame {
                background-color: #F91200; border: 5px solid black;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """)

    def set_finished(self):
        self.finished = True
        self.y_set_delay = 100
        self.execute_timer.singleShot(1500, self.stop)
        self.status_label.setText("Задача завершена!")
        self.frame.setStyleSheet("""
            #mainFrame {
                background-color: #12A900; border: 5px solid black;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """)

    def set_canceled(self):
        self.finished = True
        self.y_set_delay = 100

        self.execute_timer.stop()
        self.execute_timer.singleShot(1500, self.stop)

        self.status_label.setText("Задача отменена")

    def execute_loop(self):
        if self.finished: return
        if not (0 <= self.action_index < len(self.actions)): return self.set_finished()
        a = self.actions[self.action_index]
        self.action_index += 1

        a.run()
        self.status_label.setText(f'Шаг {self.action_index}/{len(self.actions)}: {a.get_title()}')
        self.execute_timer.singleShot(int(a.delay * 1000), self.execute_loop)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AutoClickerGui()
    window.show()
    sys.exit(app.exec())
