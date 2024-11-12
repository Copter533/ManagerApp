from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QSlider, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QPalette


class CustomSlider(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Слайдер от 0 до 360")
        self.setGeometry(300, 300, 100, 400)

        # Основной layout
        layout = QVBoxLayout()

        # Создаем метку для отображения значения
        self.value_label = QLabel("0", alignment=Qt.AlignmentFlag.AlignCenter)
        self.value_label.setFont(QFont("Arial", 24))
        layout.addWidget(self.value_label)

        # Настраиваем сам слайдер
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(360)
        self.slider.setValue(0)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self.slider.setTickInterval(30)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setInvertedAppearance(False)

        # Подключаем изменение значения к функции
        self.slider.valueChanged.connect(self.update_value)
        layout.addWidget(self.slider)

        self.setLayout(layout)

    def update_value(self, value):
        # Обновляем значение метки при изменении значения слайдера
        self.value_label.setText(str(value))


# Запуск приложения
app = QApplication([])
window = CustomSlider()
window.show()
app.exec()
