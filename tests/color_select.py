import math
import os
from typing import Iterable

from PyQt6.QtCore import Qt, QRectF, QPointF, pyqtSignal
from PyQt6.QtGui import (QColor, QConicalGradient, QPainter, QPen,
                         QLinearGradient, QBrush, QPainterPath, QStaticText)
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QMainWindow, QFrame)

from date_utils import Config
from gui_additions import LayoutBuilder, simple_label, AdvancedColorSelector


class AdvancedColorSelect1(QFrame):
    """Селектор цвета: колесо HUE + центральный квадрат для SAT/VAL"""
    colorChanged = pyqtSignal(QColor)

    def __init__(self, size=350, ring_thickness=1):
        super().__init__()

        self.wheel_size = size
        self.ring_thickness = ring_thickness

        self.setFixedSize(size, size)

        # Пометки для других цветов
        self.tracers: list[QColor] = []

        self.hue = 0
        self.sat = 255
        self.val = 255

        self.sat_pos = 1.0
        self.val_pos = 1.0

        # Состояние перетаскивания
        self.dragging_wheel = False
        self.dragging_square = False

        self.setMouseTracking(True)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self._draw_color_wheel(painter)
        self._draw_center_satval_square(painter)
        self._draw_satval_picker(painter)

        center_x = self.wheel_size / 2
        center_y = self.wheel_size / 2
        outer_radius = self.wheel_size / 2 - 3
        inner_radius = outer_radius - self.ring_thickness
        self._draw_hue_slider(painter, center_x, center_y, outer_radius, inner_radius)

        self._draw_color_preview(painter)

    def _draw_color_wheel(self, painter: QPainter):
        """Рисует цветовое колесо HUE"""
        center_x, center_y, outer_radius, inner_radius = self.get_circle_stats()

        # Фон
        painter.setBrush(QColor.fromHsv(self.hue, 200, 100))
        painter.drawEllipse(QRectF(0, 0, self.wheel_size, self.wheel_size))

        gradient = QConicalGradient(QPointF(center_x, center_y), 0)
        num_stops = 60
        for i in range(num_stops + 1):
            hue = int((i / num_stops) * 359)
            gradient.setColorAt(i / num_stops, QColor.fromHsv(hue, 255, 255))

        path = QPainterPath()
        outer_rect = QRectF(
            center_x - outer_radius,
            center_y - outer_radius,
            outer_radius * 2,
            outer_radius * 2
        )
        path.addEllipse(outer_rect)

        inner_rect = QRectF(
            center_x - inner_radius,
            center_y - inner_radius,
            inner_radius * 2,
            inner_radius * 2
        )
        path.addEllipse(inner_rect)
        path.setFillRule(Qt.FillRule.OddEvenFill)

        # Рисуем кольцо
        painter.setBrush(gradient)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPath(path)

        painter.setBrush(Qt.BrushStyle.NoBrush)

        painter.setPen(QPen(QColor(0, 0, 0, 60), 1))
        for tracer in self.tracers:
            if tracer.saturation() < 100 or tracer.value() < 100: continue
            angle = -math.radians(tracer.hue())
            painter.drawLine(
                QPointF(inner_radius * math.cos(angle) + center_x, inner_radius * math.sin(angle) + center_y),
                QPointF(outer_radius * math.cos(angle) + center_x, outer_radius * math.sin(angle) + center_y)
            )

        # Обводки
        painter.setPen(QPen(QColor(0, 0, 0), 5))
        painter.drawEllipse(outer_rect)
        painter.drawEllipse(inner_rect)

    def _draw_hue_slider(self, painter, center_x, center_y, outer_radius, inner_radius):
        """Рисует прямоугольный индикатор выбранного HUE на кольце"""
        angle_rad = -math.radians(self.hue)

        outer_x = center_x + outer_radius * math.cos(angle_rad)
        outer_y = center_y + outer_radius * math.sin(angle_rad)
        inner_x = center_x + inner_radius * math.cos(angle_rad)
        inner_y = center_y + inner_radius * math.sin(angle_rad)

        perp_angle = angle_rad + math.pi / 2
        slider_width = 10
        dx = slider_width / 2 * math.cos(perp_angle)
        dy = slider_width / 2 * math.sin(perp_angle)

        path = QPainterPath()
        path.moveTo(outer_x + dx, outer_y + dy)
        path.lineTo(outer_x - dx, outer_y - dy)
        path.lineTo(inner_x - dx, inner_y - dy)
        path.lineTo(inner_x + dx, inner_y + dy)
        path.closeSubpath()

        painter.setPen(QPen(QColor(255, 255, 255), 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)

        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.drawPath(path)

    def _draw_center_satval_square(self, painter):
        """Рисует центральный квадрат с градиентом SAT (по X) и VAL (по Y)"""
        center_x = self.wheel_size / 2
        center_y = self.wheel_size / 2
        outer_radius = self.wheel_size / 2 - 3
        inner_radius = outer_radius - self.ring_thickness

        # Размер квадрата (чуть меньше внутреннего круга)
        square_size = (self.wheel_size / 2 - 40) * 2 * math.sin(math.pi / 4) + 13
        self.get_square_size()

        square_left = center_x - square_size / 2
        square_top = center_y - square_size / 2

        square_rect = QRectF(square_left, square_top, square_size, square_size)

        # Сначала рисуем базовый цвет (выбранный HUE с полной насыщенностью и яркостью)
        base_color = QColor.fromHsv(self.hue, 255, 255)
        rounded_rect_path = QPainterPath()
        rounded_rect_path.addRoundedRect(square_rect, 30, 30)
        painter.fillPath(rounded_rect_path, base_color)

        # Горизонтальный градиент: слева белый (SAT=0), справа прозрачный (SAT=255)
        sat_gradient = QLinearGradient(square_left, square_top, square_left + square_size, square_top)
        sat_gradient.setColorAt(0, QColor(255, 255, 255, 255))
        sat_gradient.setColorAt(1, QColor(255, 255, 255, 0))

        painter.fillPath(rounded_rect_path, sat_gradient)

        # Вертикальный градиент: сверху прозрачный (VAL=255), снизу чёрный (VAL=0)
        val_gradient = QLinearGradient(square_left, square_top, square_left, square_top + square_size)
        val_gradient.setColorAt(0, QColor(0, 0, 0, 0))
        val_gradient.setColorAt(1, QColor(0, 0, 0, 255))

        painter.fillPath(rounded_rect_path, val_gradient)

        # Обводка квадрата
        bri = 0
        painter.setPen(QPen(QColor(bri, bri, bri), 5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(square_rect, 30, 30)

    def _draw_satval_picker(self, painter):
        """Рисует точку выбора SAT/VAL в центральном квадрате"""
        center_x = self.wheel_size / 2
        center_y = self.wheel_size / 2
        outer_radius = self.wheel_size / 2 - 3
        inner_radius = outer_radius - self.ring_thickness

        square_size = self.get_square_size()
        square_left = center_x - square_size / 2
        square_top = center_y - square_size / 2

        # Позиция точки
        picker_x = square_left + self.sat_pos * square_size
        picker_y = square_top + (1 - self.val_pos) * square_size  # Инвертируем Y (сверху = яркий)

        picker_radius = 8

        # Белая обводка
        painter.setPen(QPen(QColor(255, 255, 255), 4))
        painter.setBrush(self.get_color())
        painter.drawEllipse(QPointF(picker_x, picker_y), picker_radius, picker_radius)

        # Чёрная обводка
        painter.setPen(QPen(QColor(0, 0, 0), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(picker_x, picker_y), picker_radius, picker_radius)

    def _draw_color_preview(self, painter: QPainter):
        """Рисует превью цвета в углу"""
        border_size = 5
        x_size = self.width()  / 6
        y_size = self.height() / 6
        rect = QRectF(self.width() - x_size - border_size, self.height() - y_size - border_size, x_size, y_size)
        painter.setBrush(self.get_color())
        painter.setPen(QPen(QColor(0, 0, 0), border_size))
        painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            x, y = event.position().x(), event.position().y()

            if self._is_in_square(x, y):
                self.dragging_square = True
                self._update_satval_from_position(x, y)
            elif self._is_on_wheel(x, y):
                self.dragging_wheel = True
                self._update_hue_from_position(x, y)

    def mouseMoveEvent(self, event):
        x, y = event.position().x(), event.position().y()

        if self.dragging_square or self._is_in_square(x, y):
            if self.dragging_square:
                square_size, square_left, square_top = self.get_square_stats()

                # Ограничиваем позицию курсора пределами квадрата
                if not (square_left <= x <= square_left + square_size) or\
                   not (square_top  <= y <= square_top  + square_size):
                    clamped_x = max(square_left, min(x, square_left + square_size))
                    clamped_y = max(square_top, min(y, square_top + square_size))
                    self.cursor().setPos(self.mapToGlobal(QPointF(clamped_x, clamped_y).toPoint()))

                self.setCursor(Qt.CursorShape.BlankCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)

        if self.dragging_wheel:
            self._update_hue_from_position(x, y)
        elif self.dragging_square:
            self._update_satval_from_position(x, y)

    def mouseReleaseEvent(self, event):
        x, y = event.position().x(), event.position().y()
        if event.button() == Qt.MouseButton.LeftButton:
            if self.dragging_square and self._is_in_square(x, y):
                self.setCursor(Qt.CursorShape.CrossCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)

            self.dragging_wheel = False
            self.dragging_square = False

    def get_square_size(self):
        return (self.wheel_size / 2 - 40) * 2 * math.sin(math.pi / 4) - 5

    def get_circle_stats(self):
        # center_x, center_y, outer_radius, inner_radius = self.get_circle_stats()
        outer_radius = self.wheel_size / 2 - 3
        return (
            self.wheel_size / 2,
            self.wheel_size / 2,
            outer_radius,
            outer_radius - self.ring_thickness
        )

    def get_square_stats(self, size_delta=0):
        # square_size, square_left, square_top = self.get_square_stats()
        size = (self.wheel_size / 2 - 40) * 2 * math.sin(math.pi / 4) - 5 + size_delta
        return (
            size,
            (self.wheel_size - size) / 2,
            (self.wheel_size - size) / 2
        )

    def _is_on_wheel(self, x, y):
        """Для выбора тона цвета"""
        center_x, center_y, outer_radius, inner_radius = self.get_circle_stats()
        square_size, square_left, square_top = self.get_square_stats()
        distance_to_slider_sq = (x - (square_left + square_size * self.sat_pos)) ** 2 +\
                                (y - (square_top + square_size * (1 - self.val_pos))) ** 2
        if distance_to_slider_sq < 10 * 10: return False
        distance_sq = (x - center_x) ** 2 + (y - center_y) ** 2
        return inner_radius * inner_radius <= distance_sq <= outer_radius * outer_radius

    def _is_in_square(self, x, y):
        """Для выбора насыщенности и яркости"""
        square_size, square_left, square_top = self.get_square_stats(10)
        return (square_left <= x <= square_left + square_size and
                square_top <= y <= square_top + square_size)

    def _update_hue_from_position(self, x, y):
        """Обновляет HUE на основе позиции мыши"""
        center_x = self.wheel_size / 2
        center_y = self.wheel_size / 2

        dx = x - center_x
        dy = y - center_y
        angle_rad = math.atan2(dy, dx)
        angle_deg = math.degrees(angle_rad)

        self.hue = int(-angle_deg % 360)

        self.update()
        self.colorChanged.emit(self.get_color())

    def _update_satval_from_position(self, x, y):
        """Обновляет SAT/VAL на основе позиции мыши в центральном квадрате"""
        square_size, square_left, square_top = self.get_square_stats()

        # Вычисляем относительную позицию в квадрате (0-1)
        rel_x = (x - square_left) / square_size
        rel_y = (y - square_top) / square_size

        # Ограничиваем значения
        rel_x = max(0, min(1, rel_x))
        rel_y = max(0, min(1, rel_y))

        # Сохраняем позицию
        self.sat_pos = rel_x
        self.val_pos = 1 - rel_y  # Инвертируем Y

        self.sat = int(self.sat_pos * 255)
        self.val = int(self.val_pos * 255)

        self.update()
        self.colorChanged.emit(self.get_color())

    def get_color(self):
        return QColor.fromHsv(self.hue, self.sat, self.val)

    def set_color(self, color: QColor):
        self.hue = color.hue() if color.hue() != -1 else 0
        self.sat = color.saturation()
        self.val = color.value()

        self.sat_pos = self.sat / 255
        self.val_pos = self.val / 255

        self.update()
        self.colorChanged.emit(self.get_color())


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Выбор цвета!")
        self.setGeometry(100, 100, 450, 450)
        self.setStyleSheet("background-color: #FFFFFF; color: black;")

        # Лейбл для отображения текущего цвета
        self.color_label = simple_label("H:0 S:255 V:255", 30)

        # Селектор цвета
        self.color_select = AdvancedColorSelector(size=350, ring_thickness=40)
        self.color_select.colorChanged.connect(self._on_color_changed)

        os.chdir("../")
        events = Config.load("schedule_v2.json").events
        colors = [QColor.fromRgb(*event.color) for event in events]
        self.color_select.tracers.extend(colors)

        self.main_layout = (
            LayoutBuilder(QVBoxLayout)
            .addWidget(self.color_label)
            .addWidget(self.color_select)
            .build(alignment=Qt.AlignmentFlag.AlignTop)
        )

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

    def _on_color_changed(self, color):
        """Обновляет лейбл при изменении цвета"""
        self.color_label.setText(
            f"H:{color.hue()} S:{color.saturation()} V:{color.value()} | {color.name()}"
        )


if __name__ == "__main__":
    app = QApplication([])
    window = Window()
    window.show()
    app.exec()