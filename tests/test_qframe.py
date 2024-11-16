from PyQt6.QtWidgets import QApplication, QMainWindow, QFrame
from PyQt6.QtGui import QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtCore import Qt, QRectF, QRect


class CustomFrame(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Настраиваем стиль фрейма
        self.border_width = 10  # Толщина рамки
        self.setStyleSheet(f"background-color: #ffffff; border-radius: 15px; border: {self.border_width}px solid red;")
        self.icon_path = "../icons/telescope.svg"  # Путь к SVG-иконке
        self.icon_opacity = 0.5  # Прозрачность иконки
        self.icon_scale = 3  # Масштаб иконки
        self.icon_offset = (90, 90)  # Смещение иконки от правого нижнего угла

        # Загрузка SVG-иконки
        self.svg_renderer = QSvgRenderer(self.icon_path)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setClipRect(QRect(
            self.border_width // 2,
            self.border_width // 2,
            self.width()  - self.border_width,
            self.height() - self.border_width
        ))

        # Рисуем SVG-иконку
        if self.svg_renderer.isValid():
            # Определяем размер иконки из SVG
            svg_size = self.svg_renderer.defaultSize()
            icon_width = int(svg_size.width() * self.icon_scale)
            icon_height = int(svg_size.height() * self.icon_scale)

            # Учитываем толщину рамки, чтобы иконка не заходила за границы
            x = int(self.width() - icon_width - self.border_width + self.icon_offset[0])
            y = int(self.height() - icon_height - self.border_width + self.icon_offset[1])

            # Полупрозрачность
            painter.setOpacity(self.icon_opacity)

            # Рисуем SVG с использованием QSvgRenderer
            self.svg_renderer.render(painter, QRectF(x, y, icon_width, icon_height))

        painter.end()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Создаем кастомный фрейм
        self.frame = CustomFrame(self)
        self.frame.setFixedSize(200, 200)  # Размер фрейма
        self.frame.move(50, 50)  # Позиция фрейма внутри окна

        # Настраиваем главное окно
        self.setWindowTitle("SVG иконка в фрейме")
        self.setGeometry(100, 100, 400, 300)  # Размер главного окна


# Основное приложение
app = QApplication([])
window = MainWindow()
window.show()
app.exec()
