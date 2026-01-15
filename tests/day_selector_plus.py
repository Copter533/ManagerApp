import json
import json
import math
import os
import re
import sys
from abc import abstractmethod, ABC, ABCMeta
from collections import defaultdict
from datetime import datetime, date, timedelta
from math import atan2, sin, cos, radians, ceil
from time import time, sleep
from typing import Type, Iterable, Callable, Any

from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QTimer, QSharedMemory, QRectF, QPointF, QPropertyAnimation, \
    QEasingCurve, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QFontDatabase, QAction, QStandardItem, \
    QStandardItemModel, QTextOption, QEnterEvent, QConicalGradient, QPainterPath, QLinearGradient, QBrush
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QFrame, QGridLayout, QGraphicsDropShadowEffect, QSlider,
    QLineEdit, QVBoxLayout, QScrollArea, QTextEdit, QApplication, QComboBox, QMessageBox, QStyleOptionButton, QStyle,
    QLayout, QBoxLayout, QSpacerItem, QSizePolicy, QGraphicsOpacityEffect
)

from announced_task import AnnouncedTask
from gui_additions import simple_label, icon_button
from multidate_v2 import MultiDateWeekday, MultiDateMonthday, MultiDateParity, days_of_week, months, EventStamp, \
    str_to_datetime, datetime_to_str, MultiDateMixer, AllTimestampsWrapper, MultiDateEmpty
from tags import Tags, Tag, TagList
from date_utils import ScheduleEvent, rgb_to_hex, str_time, interpolate, beauty_time, \
    MultiDateHolder, beauty_date, is_main_window
from time_periods import all_periods, TimePeriod
from utils import DebugTimer


class CalendarPopup(QFrame):
    def __init__(self, parent, obj_to_edit: QWidget | Callable, pick_date: datetime | date = None,
                 main_window=None, custom_style_callback: Callable[[date, "SegmentedButton"], Any]=None,
                 disable_default_style=False):
        super().__init__(parent)
        if pick_date is None: pick_date = datetime.today()
        self.pick_date = date(pick_date.year, pick_date.month, 1)
        self.original_pick_date = pick_date.date() if isinstance(pick_date, datetime) else pick_date

        assert disable_default_style or is_main_window(main_window), 'Должен быть класс главного окна'
        self.main_window = main_window

        self.obj_to_edit = obj_to_edit
        self.custom_style_callback = custom_style_callback
        self.disable_default_style = disable_default_style

        self.setWindowFlags(Qt.WindowType.Popup)
        self.setObjectName("calendarFrame")
        self.setStyleSheet("""
            QWidget {
                background: white;
                color: black;
            }
            #calendarFrame {
                border: 2px solid #000000;
            }
        """)
        self.setFixedSize(550, 270)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0, 0, 0, 150))
        shadow.setOffset(2, 2)
        self.setGraphicsEffect(shadow)

        main_layout = QVBoxLayout()

        control_layout = QHBoxLayout()
        self.month_year_label = simple_label("...", 18)
        self.month_year_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.month_year_label.setStyleSheet("""
            color: black;
        """)
        control_layout.addWidget(icon_button("left.svg",  30, 35, 'blue', callback=lambda : self.cycle(-1)))
        control_layout.addWidget(self.month_year_label)
        control_layout.addWidget(icon_button("right.svg", 30, 35, 'blue', callback=lambda : self.cycle(+1)))

        main_layout.addLayout(control_layout)
        self.setLayout(main_layout)

        self.grid_layout = QGridLayout()
        self.grid_layout.setHorizontalSpacing(2)
        self.grid_layout.setVerticalSpacing(2)
        main_layout.addLayout(self.grid_layout)

        self.week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for col, day in enumerate(self.week_days):
            lbl = QPushButton(day)
            lbl.setFixedSize(30, 30)
            lbl.setStyleSheet(
            """
                QPushButton {
                    background: transparent;
                    border: none;
                    color: #666;
                    font-weight: bold;
                }
            """)
            lbl.setEnabled(False)
            self.grid_layout.addWidget(lbl, 0, col)

        self.day_buttons = []
        # self.update_view()

    def display(self, anchor: QWidget = None):
        self.update_position(anchor or self.parent())
        self.update_view()
        self.show()

    def update_position(self, anchor_widget: QWidget):
        btn_global_pos = anchor_widget.mapToGlobal(QPoint(0, anchor_widget.height()))
        screen_geo = self.screen().availableGeometry()

        popup_width = self.width()
        popup_height = self.height()

        # Рассчитываем позицию по X
        x = btn_global_pos.x()
        if x + popup_width > screen_geo.right():
            x = screen_geo.right() - popup_width
        x = max(x, screen_geo.left())

        # Рассчитываем позицию по Y
        y = btn_global_pos.y()
        if y + popup_height > screen_geo.bottom():
            y = btn_global_pos.y() - popup_height - anchor_widget.height()
        y = max(y, screen_geo.top())

        self.move(int(x), int(y))

    def update_view(self):
        for btn in self.day_buttons:
            btn.deleteLater()
        self.day_buttons.clear()

        self.month_year_label.setText(
            f"{months[self.pick_date.month-1][2].capitalize()} {self.pick_date.year}"
        )

        width = 6
        height = 7
        from_day = self.pick_date - timedelta(days=self.pick_date.weekday())
        to_day   = from_day + timedelta(days=width * height - 1)

        btns: list[dict] = []
        for index in range(width*height):
            day = from_day + timedelta(days=index)
            is_current_month = day.month == self.pick_date.month

            btn = SegmentedButton(day, is_bold=is_current_month)

            if day == date.today():
                btn.draw_circle_offset = -1
                btn.setStyleSheet(
                    # background: rgba(0, 120, 212, 0.8);
                    """
                        SegmentedButton {
                            border: 3px solid #0078d4;
                            border-radius: 5px;
                            background: rgba(0, 120, 212, 0.1);
                            color: black;
                            font-weight: bold;
                        }
                        SegmentedButton:hover {
                            border: 3px solid #0068c4;
                            background: rgba(0, 120, 212, 0.2);
                        }
                    """
                )

            if self.custom_style_callback is not None:
                self.custom_style_callback(day, btn)

            # noinspection PyUnresolvedReferences
            btn.clicked.connect(lambda _, d=day: self.on_date_selected(d))

            self.grid_layout.addWidget(btn, *divmod(index + 7, 7))
            self.day_buttons.append(btn)
            # noinspection PyTypeChecker
            btns.append(defaultdict(list, [("btn", btn)]))

        if not self.disable_default_style:
            events: list[ScheduleEvent] = [e for e in self.main_window.scheduled_events if not e.tags.have(Tags.HIDDEN.YES)]

            for event in events:
                for stamp in event.get_final_timestamps(from_day, to_day):
                    index = (stamp.get_date() - from_day).days
                    btns[index]["colors"].append(QColor(*event.color))
                    btns[index]["tooltips"].append(event.name)

            for entry in btns:
                if "tooltips" in entry:
                    entry["btn"].setToolTip("\n".join(entry["tooltips"]))
                entry["btn"].set_colors(entry["colors"])

    def on_date_selected(self, day):
        if isinstance(self.obj_to_edit, QWidget):
            # noinspection PyUnresolvedReferences
            self.obj_to_edit.setText(beauty_date(day))
        elif isinstance(self.obj_to_edit, Callable):
            self.obj_to_edit(day)
        self.hide()

    def cycle(self, offset):
        for _ in range(abs(offset)):
            self.pick_date = (self.pick_date.replace(day=1) + timedelta(days=31 if offset > 0 else -1)).replace(day=1)
        self.update_view()


class MonthPickerTimeline(QFrame):
    def __init__(self):
        super().__init__()


class SegmentedButton(QPushButton):
    def __init__(self, day: date, is_bold, colors=None, parent=None):
        super().__init__(str(day.day))
        self.setParent(parent)
        self.colors = colors or []
        self.setFixedSize(30, 30)
        self.is_bold = is_bold

        self.ignore_paint = False
        self.crossed = False

        self.draw_circle_offset = 2

        self.setStyleSheet(
        f"""
            SegmentedButton {{
                border: {'1px solid #ccc' if is_bold else '1px solid #aaa'};
                border-radius: 15px;
                background: transparent;
                color: black;
                {'font-weight: bold;' if is_bold else ''}
            }}
            SegmentedButton:hover {{
                background: rgba(0,0,0,0.1);
            }}
        """)

    def set_colors(self, colors):
        self.colors = colors

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.ignore_paint: return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.colors:
            rect = QRectF(
                self.draw_circle_offset, self.draw_circle_offset,
                self.width() - self.draw_circle_offset * 2, self.height() - self.draw_circle_offset * 2)

            angle_offset = len(self.colors) * 45 - 45 if 1 <= len(self.colors) <= 2 else 0
            angle = 360.0 / len(self.colors)

            painter.setPen(QColor(0, 0, 0, 0))
            for i, color in enumerate(self.colors):
                color.setAlpha(120)
                painter.setBrush(color)
                painter.drawPie(rect, int(i * angle * 16 + angle_offset * 16), int(angle * 16))

        if self.crossed:
            painter.setPen(QPen(QColor(255, 0, 0), 2))  # Красная линия толщиной 2px

            # Рисуем крест (две диагональные линии)
            margin = 3  # Отступ от краев
            painter.drawLine(margin, margin,
                             self.width() - margin, self.height() - margin)
            painter.drawLine(self.width() - margin, margin,
                             margin, self.height() - margin)

        opt = QStyleOptionButton()
        self.initStyleOption(opt)

        # Убираем фон у опции
        opt.features &= ~QStyleOptionButton.ButtonFeature.Flat
        opt.palette.setColor(self.backgroundRole(), Qt.GlobalColor.transparent)

        # Рисуем стандартные элементы кнопки
        self.style().drawControl(QStyle.ControlElement.CE_PushButton, opt, painter, self)


if __name__ == '__main__':
    app = QApplication([])
    os.chdir("../")
    window = CalendarPopup(None, print, disable_default_style=True)
    window.display(window)
    app.exec()