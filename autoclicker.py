import json
import sys

from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import QApplication, QFrame, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt, QTimer

from gui_additions import simple_label, icon_button
from announced_task import AnnouncedTask


class AutoClickerGui(QFrame):
    def __init__(self, filename):
        super().__init__()

        with open(f"announced_tasks/{filename}", "r", encoding="UTF-8") as f:
            self.task = AnnouncedTask.from_json(json.load(f))
            self.task.on_finished = self.set_finished

        # Настройка окна
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool  # Для исключения из панели задач
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # Прозрачный фон

        self.frame = QFrame()
        self.frame.setMinimumWidth(600)
        self.frame.setFixedHeight(55)
        self.frame.setObjectName("mainFrame")

        self.status_label = simple_label("", 15)
        self.stop_button  = icon_button("remove.svg", 30, 35, 'red',
                                        callback=self.set_canceled)

        self.min_pos = -60
        self.max_pos = -5

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

        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        self.set_started()
        self.execute_timer.singleShot(500, self.execute_loop)

    def resizeEvent(self, a0):
        w = QGuiApplication.primaryScreen().size().width()
        self.move((w - self.width()) // 2, self.y())

    def set_y_pos(self):
        if self.y_set_delay > 0:
            self.y_set_delay -= 1
            return

        target = self.min_pos if self.task.is_finished() else self.max_pos
        self.base_pos += (target - self.base_pos) / 10
        self.move(self.x(), int(self.base_pos))

    def stop(self):
        self.close()
        exit(0)

    def set_started(self):
        self.status_label.setText("Запуск задачи...")
        self.frame.setStyleSheet("""
            #mainFrame {
                background-color: #F91200; border: 5px solid black;
                border-bottom-left-radius: 20px;
                border-bottom-right-radius: 20px;
            }
        """)

    def set_finished(self):
        self.task.finish()
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
        if self.task.is_finished(): return

        self.task.finish()
        self.y_set_delay = 100

        self.execute_timer.stop()
        self.execute_timer.singleShot(1500, self.stop)

        self.status_label.setText("Задача отменена")

        # AnnouncedTask(0, [SendNotification(None, "Титул", "1\n2\n3")]).execute_loop()

    def execute_loop(self):
        a = self.task.execute_loop()
        if not a: return

        self.status_label.setText(f'Шаг {self.task.get_index()}/{len(self.task.actions)}: {a.get_title()}')
        self.execute_timer.singleShot(int(a.delay * 1000), self.execute_loop)


if __name__ == "__main__":
    if len(sys.argv) <= 1: raise ValueError("Требуется название файла со сценарием")

    app = QApplication(sys.argv)
    window = AutoClickerGui(sys.argv[1])
    window.show()
    sys.exit(app.exec())

    # t = AnnouncedTask(0, [
    #     PressHotKey("Win+D"),
    #     PressHotKey("Win+1"),
    #     PressHotKey("Alt+F4"),
    #     PressHotKey("Win+5", delay=1),
    # ])
