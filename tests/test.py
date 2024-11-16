from random import randint

from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PyQt6.QtCore import Qt, QRect, QPoint
from PyQt6.QtGui import QPainter, QPen, QColor


class RangeSlider(QWidget):
    def __init__(self, min_value=0, max_value=24):
        super().__init__()
        self.min_value = min_value * 6
        self.max_value = max_value * 6
        self.current_min = self.min_value
        self.current_max = self.max_value

        self.slider_height = 20
        self.handle_radius = 16
        self.active_handle = None
        self.last_active_handle = None

        self.setFixedHeight(70)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Устанавливаем фокус для обработки клавиш

    @staticmethod
    def get_timestr(value, leading_zero=True):
        h, m = divmod(value * 10, 60)
        return f'{"0" if h < 10 and leading_zero else ""}{h}:{"0" if m < 10 else ""}{m}'

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.paint_background(painter)
        self.paint_duration(painter)
        self.paint_marker('min', painter, QColor(50, 100, 200), self.value_to_position(self.current_min))
        self.paint_marker('max', painter, QColor(200, 50,  50), self.value_to_position(self.current_max))

    def paint_background(self, painter):
        y = (self.height() - self.slider_height) // 2
        track_rect = QRect(
            self.handle_radius,
            y,
            self.width() - 2 * self.handle_radius,
            self.slider_height
        )
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(100, 100, 100))
        painter.drawRect(track_rect)

    def paint_duration(self, painter: QPainter):
        x1 = self.value_to_position(self.current_min)
        x2 = self.value_to_position(self.current_max)
        y  = (self.height() - self.slider_height) // 2
        offset = 8
        painter.setPen(QPen(QColor(255, 255, 255), 8))
        painter.drawRect(QRect(
            x1      + 1, y                  + offset,
            x2 - x1 - 2, self.slider_height - offset * 2
        ))
        if x2 - x1 > 50:
            painter.setPen(QColor(0, 0, 0))
            f = painter.font()
            f.setPointSize(10)
            f.setBold(True)
            painter.setFont(f)

            painter.drawText((x1 + x2) // 2 - 14, self.height() // 2 + 5, self.get_timestr(self.current_max - self.current_min, False))

    def paint_marker(self, type_, painter: QPainter, color, x):
        y = self.height() // 2
        dx = 7

        painter.setPen(QPen(color, dx))
        painter.drawLine(x, y-5, x, y+5)

        f = painter.font()
        f.setPointSize(15)
        f.setBold(True)
        painter.setFont(f)
        if type_ == 'min': painter.drawText(x-11, y-20, self.get_timestr(self.current_min))
        if type_ == 'max': painter.drawText(x-40, y+35, self.get_timestr(self.current_max))

        painter.setPen(QPen(QColor.fromHsv(color.hue(), color.saturation(), color.value()-40), dx))
        painter.drawPolygon([QPoint(x, y+dx), QPoint(x+dx, y+dx*2), QPoint(x-dx, y+dx*2)])

        painter.setPen(QPen(QColor.fromHsv(color.hue(), color.saturation(), color.value()+40), dx))
        painter.drawPolygon([QPoint(x, y-dx), QPoint(x+dx, y-dx*2), QPoint(x-dx, y-dx*2)])

    def mousePressEvent(self, event):
        # Проверка попадания в маркеры
        if self.handle_hit(event.pos(), self.current_min):
            self.active_handle = 'min'
            self.last_active_handle = 'min'
        elif self.handle_hit(event.pos(), self.current_max):
            self.active_handle = 'max'
            self.last_active_handle = 'max'

    def mouseMoveEvent(self, event):
        if self.active_handle is None: return
        value = self.position_to_value(event.position().x())
        if self.active_handle == 'min':
            self.current_min = min(max(self.min_value, value), self.current_max - 1)
        elif self.active_handle == 'max':
            self.current_max = max(min(self.max_value, value), self.current_min + 1)

        self.update()

    def mouseReleaseEvent(self, event):
        self.active_handle = None

    def keyPressEvent(self, event):
        if not self.last_active_handle: return
        step = 1  # Шаг изменения значения
        if event.key() == Qt.Key.Key_Left:
            if self.last_active_handle == 'min' and self.current_min > self.min_value:
                self.current_min -= step
            if self.last_active_handle == 'max' and self.current_max > self.current_min + 1:
                self.current_max -= step
        elif event.key() == Qt.Key.Key_Right:
            if self.last_active_handle == 'min' and self.current_min < self.current_max - 1:
                self.current_min += step
            if self.last_active_handle == 'max' and self.current_max < self.max_value:
                self.current_max += step

        self.update()

    def handle_hit(self, pos, value):
        handle_pos = QPoint(self.value_to_position(value), self.height() // 2)
        return (pos - handle_pos).manhattanLength() <= self.handle_radius * 2

    def value_to_position(self, value):
        return int((value - self.min_value) / (self.max_value - self.min_value) * (
                    self.width() - 2 * self.handle_radius) + self.handle_radius)

    def position_to_value(self, x):
        return int((x - self.handle_radius) / (self.width() - 2 * self.handle_radius) * (
                    self.max_value - self.min_value) + self.min_value)


app = QApplication([])
window = QWidget()
l = QVBoxLayout()
for i in range(10):
    l.addWidget(RangeSlider())
window.setLayout(l)
window.show()
app.exec()
