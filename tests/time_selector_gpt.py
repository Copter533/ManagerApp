import os
import re
from typing import Optional, Tuple, List, Callable, Any
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer, QPoint, QSize, QRect, QEasingCurve, QPropertyAnimation
from PyQt6.QtGui import QPainter, QFont, QColor, QAction, QIcon, QBrush, QMouseEvent
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QMainWindow, QLineEdit, QScrollArea, QFrame,
                             QComboBox, QLabel, QPushButton, QSizePolicy, QHBoxLayout, QLayout, QGridLayout, QDialog)

from date_utils import Config, str_time
from gui_additions import LayoutBuilder, EventButton, new_separator, load_font, icon_button, simple_label, \
    simple_combo_box, recolor_icon, set_color_scheme
from multidate_v2 import MultiDateMixer
from tags import Tags

from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QPoint, QTimer, QPropertyAnimation
from PyQt6.QtWidgets import QWidget, QApplication
from PyQt6.QtGui import QPainter, QPen, QColor, QLinearGradient, QFont, QFontMetrics


class TimeSelector(QWidget):
    def __init__(self, min_value=0, max_value=24):
        super().__init__()
        self.min_value = min_value * 60
        self.max_value = max_value * 60
        self.min_limit = self.min_value
        self.max_limit = self.max_value

        self._step_max = 10
        self._step_min = 1

        self.slider_height = 20
        self.handle_radius = 16
        self.active_handle = None
        self.last_active_handle = None

        self.is_popup = False

        self.setFixedHeight(70)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # Устанавливаем фокус для обработки клавиш

    def set_min(self, new_min): self.min_value = max(self.min_limit, new_min)
    def set_max(self, new_max): self.max_value = min(self.max_limit, new_max)

    def get_step(self):
        return \
            (self._step_min
                if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier else
            self._step_max)

    @staticmethod
    def get_timestr(value, leading_zero=True):
        return str_time(value, leading_zero=leading_zero)

    def get_timedur(self):
        return f'{self.get_timestr(self.min_value)}-{self.get_timestr(self.max_value)}'

    def get_time_list(self):
        return self.min_value, self.max_value

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.paint_background(painter)
        self.paint_between(painter)
        self.paint_marker('min', painter, QColor(50, 100, 200), self.value_to_position(self.min_value))
        self.paint_marker('max', painter, QColor(200, 50,  50), self.value_to_position(self.max_value))
        self.paint_duration(painter)

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

    def paint_between(self, painter: QPainter):
        x1 = self.value_to_position(self.min_value)
        x2 = self.value_to_position(self.max_value)
        y  = (self.height() - self.slider_height) // 2
        offset = 8
        painter.setPen(QPen(QColor(255, 255, 255), 8))
        painter.drawRect(QRect(
            x1      + 1, y                  + offset,
            x2 - x1 - 2, self.slider_height - offset * 2
        ))

    def paint_duration(self, painter: QPainter):
        x = (self.value_to_position(self.min_value) + self.value_to_position(self.max_value)) // 2

        painter.setPen(QColor(0, 0, 0))
        f = painter.font()
        f.setPointSize(10)
        f.setBold(True)
        painter.setFont(f)

        painter.drawText(x - 14, self.height() // 2 + 5, self.get_timestr(self.max_value - self.min_value, False))

    def paint_marker(self, type_, painter: QPainter, color, x):
        y = self.height() // 2
        dx = 7

        painter.setPen(QPen(color, dx))
        painter.drawLine(x, y-5, x, y+5)

        f = painter.font()
        f.setPointSize(15)
        f.setBold(True)
        painter.setFont(f)
        if type_ == 'min': painter.drawText(x - 11, y - 20, self.get_timestr(self.min_value))
        if type_ == 'max': painter.drawText(x - 40, y + 35, self.get_timestr(self.max_value))

        painter.setPen(QPen(QColor.fromHsv(color.hue(), color.saturation(), color.value()-40), dx))
        # noinspection PyTypeChecker
        painter.drawPolygon([QPoint(x, y+dx), QPoint(x+dx, y+dx*2), QPoint(x-dx, y+dx*2)])

        painter.setPen(QPen(QColor.fromHsv(color.hue(), color.saturation(), color.value()+40), dx))
        # noinspection PyTypeChecker
        painter.drawPolygon([QPoint(x, y-dx), QPoint(x+dx, y-dx*2), QPoint(x-dx, y-dx*2)])

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.RightButton:
            if self.is_popup:
                self.parent().accept()
                return
            else:
                popup = TimeSelectorPopup(self.min_limit // 60, self.max_limit // 60, parent=self)
                popup.selector.min_limit = self.min_limit
                popup.selector.max_limit = self.max_limit
                popup.selector.set_min(self.min_value)
                popup.selector.set_max(self.max_value)
                center = self.mapToGlobal(self.rect().center())
                popup.move(center.x() - popup.final_size.width() // 2, center.y() - popup.final_size.height() // 2)
                if popup.exec() == QDialog.DialogCode.Accepted:
                    self.min_value = popup.selector.min_value
                    self.max_value = popup.selector.max_value
                    self.update()
                return

        closest = min((
            ('min', self.handle_dist(event.pos(), self.min_value)),
            ('max', self.handle_dist(event.pos(), self.max_value))
        ), key=lambda x: x[1])
        if closest[1] > self.handle_radius: return

        self.active_handle      = closest[0]
        self.last_active_handle = closest[0]

    def mouseMoveEvent(self, event):
        if self.active_handle is None: return
        value = round(self.position_to_value(event.position().x()) / self.get_step()) * self.get_step()
        if self.active_handle == 'min':
            self.min_value = min(max(self.min_limit, value), self.max_value)
        elif self.active_handle == 'max':
            self.max_value = max(min(self.max_limit, value), self.min_value)

        self.update()

    def mouseReleaseEvent(self, event):
        self.active_handle = None

    def keyPressEvent(self, event):
        if not self.last_active_handle: return
        if event.key() == Qt.Key.Key_Left:
            if self.last_active_handle == 'min' and self.min_value > self.min_limit:
                self.min_value = max(self.min_limit, min(self.max_limit, self.min_value - self.get_step()))
            if self.last_active_handle == 'max' and self.max_value > self.min_value + self.get_step():
                self.max_value = max(self.min_limit, min(self.max_limit, self.max_value - self.get_step()))
        elif event.key() == Qt.Key.Key_Right:
            if self.last_active_handle == 'min' and self.min_value < self.max_value - self.get_step():
                self.min_value = max(self.min_limit, min(self.max_limit, self.min_value + self.get_step()))
            if self.last_active_handle == 'max' and self.max_value < self.max_limit:
                self.max_value = max(self.min_limit, min(self.max_limit, self.max_value + self.get_step()))

        self.update()

    def handle_dist(self, pos, value):
        handle_pos = QPoint(self.value_to_position(value), self.height() // 2)
        return (pos - handle_pos).manhattanLength()

    def value_to_position(self, value):
        return int((value - self.min_limit) / (self.max_limit - self.min_limit) * (
                    self.width() - 2 * self.handle_radius) + self.handle_radius)

    def position_to_value(self, x):
        return int((x - self.handle_radius) / (self.width() - 2 * self.handle_radius) * (
                self.max_limit - self.min_limit) + self.min_limit)


class TimeSelectorPopup(QDialog):
    def __init__(self, min_value=0, max_value=24, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setWindowTitle("Выбор времени")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setStyleSheet("background: transparent;")

        self.initial_size = QSize(200, 100)
        self.final_size = QSize(800, 300)
        self.setFixedSize(self.initial_size)

        self.selector = TimeSelector(min_value, max_value)
        self.selector.is_popup = True
        self.selector.slider_height = 40
        self.selector.handle_radius = 32
        self.selector.setFixedSize(self.initial_size)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.selector)
        main_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(main_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.animation = QPropertyAnimation()
        self.animation.setDuration(500)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.valueChanged.connect(self.animate_size)
        self.animation.start()

    def animate_size(self, t):
        width = self.initial_size.width() + t * (self.final_size.width() - self.initial_size.width())
        height = self.initial_size.height() + t * (self.final_size.height() - self.initial_size.height())
        new_size = QSize(int(width), int(height))
        self.setFixedSize(new_size)
        self.selector.setFixedSize(new_size)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Выбор времени ПЛЮС")
        self.setGeometry(100, 100, 450, 450)
        self.setStyleSheet("background-color: #FFFFFF; color: black;")

        self.main_layout = (
            LayoutBuilder(QVBoxLayout)
            .addWidget(simple_label("Выбери временные промежутки:", 25))
            .addWidget(new_separator(h=5))
            .addWidget(TimeSelector())
            .build(alignment=Qt.AlignmentFlag.AlignTop)
        )

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)


if __name__ == "__main__":
    app = QApplication([])
    window = Window()
    window.show()
    app.exec()