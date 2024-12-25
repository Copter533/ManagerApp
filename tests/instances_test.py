import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox
from PyQt6.QtCore import QSharedMemory, QTimer

class SingleInstanceApplication(QApplication):
    def __init__(self, *args, unique_key):
        super().__init__(*args)
        self.shared_memory = QSharedMemory(unique_key)
        if self.shared_memory.attach():
            # Если другая копия уже работает, отправляем сигнал.
            self.alert_other_instance()
            sys.exit(0)
        else:
            # Попытка захватить shared memory
            if not self.shared_memory.create(1):
                QMessageBox.critical(None, "Ошибка", "Не удалось создать уникальный маркер для приложения")
                sys.exit(1)

    def alert_other_instance(self):
        # QMessageBox.information(None, "Уведомление", "Приложение уже запущено.")
        # Тут можно дополнительно добавить сигнал для поднятия окна
        pass
        print("Multiple runs")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Пример Single Instance")
        self.resize(400, 300)

def main():
    app = SingleInstanceApplication(sys.argv, unique_key="my_unique_key_example")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
