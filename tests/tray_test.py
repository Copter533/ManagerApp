from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMainWindow, QMenu
from PyQt6.QtGui import QIcon, QAction  # Переместили импорт QAction
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Пример с системным треем")

        # Создаем иконку для системного трея
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("../icons/list.svg"))  # Укажите путь к иконке

        # Устанавливаем контекстное меню для иконки в трее
        self.tray_menu = QMenu()

        # Добавляем действия в меню
        open_action = QAction("Открыть окно", self)
        open_action.triggered.connect(self.show_main_window)

        notify_action = QAction("Показать уведомление", self)
        notify_action.triggered.connect(lambda: self.show_notification("Заголовок", "Текст уведомления"))

        quit_action = QAction("Выход", self)
        quit_action.triggered.connect(app.quit)

        # Добавляем действия в меню
        self.tray_menu.addAction(open_action)
        self.tray_menu.addAction(notify_action)
        self.tray_menu.addSeparator()
        self.tray_menu.addAction(quit_action)

        # Устанавливаем меню для иконки в трее
        self.tray_icon.setContextMenu(self.tray_menu)

        # Активируем значок системного трея
        self.tray_icon.setVisible(True)

    def show_main_window(self):
        # Показывает главное окно приложения
        self.show()

    def show_notification(self, title, message):
        # Отображает уведомление
        if self.tray_icon.isSystemTrayAvailable():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                5000  # 5 секунд
            )
    def closeEvent(self, a0):
        self.hide()
        a0.ignore()

app = QApplication(sys.argv)

# Инициализация основного окна
window = MainWindow()
window.setGeometry(100, 100, 400, 200)

# Запуск приложения
window.show()
sys.exit(app.exec())
