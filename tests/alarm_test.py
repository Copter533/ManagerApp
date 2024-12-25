import sys

from PyQt6.QtGui import QAction, QIcon
from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

class TrayApp:
    def __init__(self):
        self.app = QApplication(sys.argv)

        # Создаем иконку для системного трея
        self.tray_icon = QSystemTrayIcon()
        self.tray_icon.setIcon(QIcon("../icons/app.svg"))

        menu = QMenu()
        exit_action = QAction("Выход", self.app)
        exit_action.triggered.connect(self.exit_app)
        menu.addAction(exit_action)
        self.tray_icon.setContextMenu(menu)

        # Подключаем сигнал нажатия на иконку
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        # Показываем иконку
        self.tray_icon.show()

        # Показываем уведомление
        self.show_notification()

    def show_notification(self):
        self.tray_icon.showMessage(
            "Уведомление",
            "Это ваше уведомление! Нажмите на него, чтобы закрыть.",
            QSystemTrayIcon.MessageIcon.Information, 1000)

    def on_tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Закрываем уведомление при нажатии
            self.tray_icon.hide()

    def exit_app(self):
        self.tray_icon.hide()
        self.app.quit()

if __name__ == "__main__":
    tray_app = TrayApp()
    sys.exit(tray_app.app.exec())
