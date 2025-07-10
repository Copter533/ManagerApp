import os
import re
import sys
import calendar
import traceback
import threading
from datetime import datetime, timedelta, date
from random import randint

from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, QPoint, QRectF, QRect, QDate, QPointF
from PyQt6.QtGui import QIcon, QFont, QColor, QPainter, QPen, QPaintDevice
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QFrame, QPushButton, QHBoxLayout, \
    QLabel, QScrollArea, QSizePolicy, QGridLayout, QGraphicsOpacityEffect, QSystemTrayIcon, QMenu, QTimeEdit, QDateEdit
from sympy import Integer

from app_killer import app_killer_thread
from gui_additions import DateSelector, simple_label, icon_button, set_color_scheme, load_font, \
    new_separator, simple_button, ui_shadow, TagSelectButton, color_select_slider, simple_line_input, CancelDate, \
    EventSelector, simple_text_input, simple_tray_action, recolor_icon, draw_arrow, \
    paint_highlighted_border, UpcomingEvents, AnnouncedTaskSelect, AnnouncedTaskSetup, framed_ui, set_size_prop, \
    SingleInstanceApplication, sidebars_ui, DaySelector, TimePeriodSelector, InvalidSettingException, ErrorArrowDrawer, \
    sidebars_layout
from tags import Tags, TagList
from utils import months, days_of_week, ScheduleEvent, MultiDate, rgb_to_hex, Config, str_time, log_error, \
    beauty_time, DebugTimer, DisplayModes

class ScheduleEventView(QFrame):
    def __init__(self, parent, app, event: ScheduleEvent, stamp: dict):
        super().__init__()
        self.setParent(parent)
        app: MainWindow
        parent: TimeColumnView

        self.app: MainWindow = app
        self.now: date = parent.now
        self.stime = stamp[0]
        self.etime = stamp[1]

        self._event = event # Не юзать дату отсюда!
        self.name  = event.name
        self.color = event.color

        self.frame     = 0
        self.important = False
        self.expired   = False

        self._highlight_color = None
        self._highlight_speed = None

        self.bgr_renderer = None

        where = event.tags.get(Tags.WHERE)
        if where:
            self.set_background_icon(where.payload.get("icon"))

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.create_ui_title()
        self.create_ui_time()
        self.create_ui_callback_button()

        if event.desc:
            newline = "\n"
            self.setToolTip(f"""<div style="text-align: center; font-size: 20px;">
                <b>Описание:</b></div>
                {"<br>".join(event.desc.split(newline))}
            """)

        self.setLayout(self.layout)
        self.show()

        self.important_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.important_timer.timeout.connect(self.next_frame)

        self.expires_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.expires_timer.timeout.connect(self.check_expired)

        self.update_style()

    def set_highlighted(self, r, g, b, speed):
        self._highlight_color = (r, g, b)
        self._highlight_speed = speed

    def set_background_icon(self, path, scale=1.2, offset_x=60, offset_y=70):
        self.bgr_renderer = QSvgRenderer(f"icons/{path}")
        if not self.bgr_renderer.isValid():
            self.bgr_renderer = QSvgRenderer(f"icons/404.svg")
        svg_size = self.bgr_renderer.defaultSize()
        self.bgr_icon_width  = int(svg_size.width()  * scale)
        self.bgr_icon_height = int(svg_size.height() * scale)
        self.bgr_offset_x = offset_x
        self.bgr_offset_y = offset_y

    def set_color(self, border: str, alpha):
        self.setStyleSheet(f"""
            #eventFrame {{
                background-color: rgba({self.color[0]}, {self.color[1]}, {self.color[2]}, {alpha});
                border-radius: 19px;
                border: {border};
                padding: 10px;
            }}
            QToolTip {{
                background-color: #333;
                color: #fff;
                border: 2px solid #888;
                padding: 5px;
                font-size: 14px;
                font-family: calibri;
            }}
        """)

    def update_style(self):
        self.important_timer.stop()
        self.expires_timer.stop()

        # 10px solid rgb(30, 30, 30)
        self.setObjectName("eventFrame")
        self.set_color("5px solid black", 200)

        if self.check_expired(): self.make_expired()
        elif self._event.times > 0:
            self.expires_timer.start(1000)

        if Tags.TRANSPARENT.YES in self._event.tags or self.expired:
            self.set_transparency(0.3)
        else:
            self.set_transparency(0.999)

        if Tags.IMPORTANT.YES in self._event.tags:
            self.make_important()

    def set_transparency(self, opacity):
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(opacity)
        self.setGraphicsEffect(opacity_effect)

    def make_expired(self):
        self.expired = True
        self.expires_timer.stop()

    def make_important(self):
        if self.expired:
            self.set_highlighted(100, 100, 100, 200)
        else:
            self.set_highlighted(255,   0,   0, 100)

        self.important = True
        self.important_timer.start(1_000 // 60)

        self.set_color("10px solid rgb(30, 30, 30);", 250)

    def get_where(self):
        return self._event.tags.get(Tags.WHERE)

    def get_tags(self):
        return self._event.tags

    def is_today(self):
        return self.now == self.app.get_now().date()

    def get_event_and_time(self):
        return self._event, self.stime, self.etime

    def check_expired(self):
        if self._event.times == 0: return False
        if self.expired: return True

        now = self.app.get_now()
        stamp_now = now.hour * 60 + now.minute
        if self.now < now.date(): return True

        stamps = self._event.get_timestamps(now)

        if not stamps: return False
        for stamp in stamps:
            if stamp[1] > stamp_now:
                return False
        return True

    def create_ui_title(self):
        lb = QLabel()
        if self.app.loaded or re.fullmatch(r"[a-zа-яё0-9 ]*", self.name, re.IGNORECASE):
            lb.setText(f'<div style="line-height: 0.9;">{self.name}</div>')
        else:
            def load():
                try:
                    lb.setText(f'<div style="line-height: 0.9;">{self.name}</div>')
                except:
                    pass

            # Эмодзи сжирают время при загрузке, поэтому их подгружаем по позже
            self._title_setter = QTimer()
            self._title_setter.singleShot(1500, load)

        lb.setFont(QFont(self.app.font_skolar, 20))
        lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lb.setWordWrap(True)
        lb.setStyleSheet("""
            background: transparent;
        """)
        ui_shadow(lb)

        self.layout.addWidget(lb)

    def create_ui_time(self):
        self.time_texts = MultiDate.time_stamp_to_str([self.stime, self.etime]).split('-')
        self.time_label = QLabel(" - ".join(self.time_texts))
        self.time_label.setFont(QFont(self.app.font_skolar, 16))
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_label.setStyleSheet("""
            background: transparent;
        """)
        ui_shadow(self.time_label)

        self.layout.addWidget(self.time_label)

    def create_ui_callback_button(self):
        button = QPushButton("Изменить")
        button.setFont(QFont(self.app.font_skolar, 15))
        button.setStyleSheet("""
                    background: transparent;
                """)
        ui_shadow(button)

        # noinspection PyUnresolvedReferences
        button.clicked.connect(self.callback_button)

        self.layout.addStretch(0)
        self.layout.addWidget(button)

    def callback_button(self):
        self.task_form = TaskForm(self.app, self._event, when=self.now)
        self.task_form.show()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.bgr_renderer:
            self.paint_background_icon()
        if self._highlight_color is not None and self._highlight_speed is not None:
            paint_highlighted_border(self, self.frame,
                                     QColor(*self._highlight_color),
                                     self._highlight_speed)

    def next_frame(self):
        if not self.important: return
        self.frame += 1
        self.update()

    def paint_background_icon(self):
        painter = QPainter(self)
        painter.setOpacity(0.3 if self.is_today() else 0.1)

        border_width = 10
        painter.setClipRect(QRect(
            border_width // 2,
            border_width // 2,
            self.width()  - border_width,
            self.height() - border_width
        ))

        x = int(self.width()  - self.bgr_icon_width  - border_width + self.bgr_offset_x)
        y = int(self.height() - self.bgr_icon_height - border_width + self.bgr_offset_y)

        self.bgr_renderer.render(painter, QRectF(x, y, self.bgr_icon_width, self.bgr_icon_height))

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        # noinspection PyTypeChecker
        p: TimeColumnView = self.parent()

        w = int(p.width() * .95)
        y1, y2, h = 0, 100, None

        if self.app.display_mode == DisplayModes.FIELD:
            y1 = (self.stime / 60 - p.min_hour) * p.per_hour
            y2 = (self.etime / 60 - p.min_hour) * p.per_hour

        elif self.app.display_mode == DisplayModes.LIST:
            i = self.app.list_mode_match.get(self, 0)
            max_no = self.app.list_mode_match.get("max_no", 1)

            total_height = self.app.schedule_scroll.height()
            y1 = i / max_no * total_height - 15
            h = total_height / max_no - 15

        self.setGeometry((p.width() - w) // 2, int(y1 + p.margin), w, int(h or y2 - y1))

        self.time_label.setText((" - " if w > 170 else "\n").join(self.time_texts))
        if self.app.display_mode != DisplayModes.LIST:
            self.time_label.setHidden(self.height() < 200)

    def __hash__(self):
        return hash(self.stime) + hash(self.etime) + hash(self.name)

    def __eq__(self, other):
        if not isinstance(other, ScheduleEventView): return False
        return (
            self._event == other._event and
            self.stime  == other.stime  and
            self.etime  == other.etime
        )


class TimeColumnView(QFrame):
    min_hour = 8
    max_hour = 24

    def __init__(self, app, i, now, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.i = i
        self.app: MainWindow = app
        self.now: date = now
        self.original_now = now
        self.margin = 20

        self.times = set()
        self.views: list[ScheduleEventView] = []

        self.is_free      = True
        self.is_important = False

        self.set_view_height(self.app.views_height)

        self.timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.update)
        self.timer.start(1 if self.app.mock_time else 1_000)

    def is_today(self):
        return self.app.get_now().date() == self.now

    def set_view_height(self, v: int):
        self.setFixedHeight(v)
        self.per_hour = (self.height() - self.margin * 2) / (self.max_hour - self.min_hour)

    def update_views(self):
        self.set_view_height(self.app.views_height)
        self.now = self.original_now + timedelta(self.app.day_offset)
        self.setStyleSheet(
            "background-color: #55EEEEEE;" if self.now.weekday() % 2 else "background-color: #55DDDDDD;"
        )

        for view in self.views:
            view.deleteLater()
        self.views.clear()
        events_and_stamps = []

        # Сброс переменных
        self.is_free      = True
        self.is_important = False

        for event in self.app.scheduled_events:
            if not event.can_occur(self.now): continue
            stamps = event.get_timestamps(self.now)
            for stamp in stamps:
                events_and_stamps.append([event, stamp])

        # Проверка пересечений
        for event1, stamp1 in events_and_stamps:
            event: ScheduleEvent
            for i, (event2, stamp2) in enumerate(events_and_stamps):
                if event1 == event2: continue
                if stamp1 is None: continue
                if stamp2 is None: continue
                if not event1.can_block(event2): continue
                if not event1.get_timestamps(self.now): continue
                if not event2.get_timestamps(self.now): continue
                if not (max(stamp1[0], stamp2[0]) <= min(stamp1[1], stamp2[1])): continue
                events_and_stamps[i][1] = None

        for event, stamp in events_and_stamps:
            if stamp is None: continue
            se = ScheduleEventView(self, self.app, event, stamp)
            if event.tags.have(Tags.TRANSPARENT.YES):
                self.views.insert(0, se)
                se.lower()
            else: self.views.append(se)
            if event.tags.have_to_go():
                self.is_free = False
            if se.important and not se.check_expired():
                self.is_important = True

        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.app.display_mode == DisplayModes.FIELD:
            self.paint_sleep_reminder() # self.blocked_hour
            self.paint_timestamps()

            if self.is_free: self.paint_no_tasks()
            else:            self.paint_between_tasks()

            self.paint_current_time_line()

        elif self.app.display_mode == DisplayModes.LIST:
            pass

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        if self.app.display_mode in [DisplayModes.LIST]:
            self.set_view_height(self.app.schedule_scroll.height() - 2)

        for event in self.views: event.resizeEvent(a0)

    def paint_timestamps(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(0, self.margin)

        font = painter.font()
        font.setPointSize(20)
        painter.setFont(font)

        alpha = 160 if self.is_today() else 10

        for hour in range(self.min_hour, self.max_hour + 1):
            for i in range(6):
                sub_y = int(self.per_hour * i / 6)

                if hour == self.max_hour: sub_y -= 1

                painter.setPen(QPen(QColor(255, 0, 0, min(255, alpha*2)) if i == 0 and self.is_today() else QColor(30, 30, 30, alpha), 2))
                painter.drawLine(self.width(), sub_y, self.width() - 10, sub_y)
                painter.drawLine(0,            sub_y, 10,                sub_y)

                if hour == self.max_hour: break

            painter.setPen(QPen(QColor(30, 30, 30, 20), 1))
            if not hour == self.blocked_hour:
                painter.drawText(15, 10, f'{"0" if hour < 10 else ""}{hour}:00')

            painter.translate(0, self.per_hour)

    def paint_no_tasks(self):
        y = 0
        y_offset = 360

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.rotate(-90)
        painter.translate(0, self.width()-20)

        font = painter.font()
        font.setPointSize(40)
        painter.setFont(font)
        painter.setPen(QColor(30, 30, 30, 20))

        while True:
            painter.drawText(-300, 0, "Свободный")
            y += y_offset
            painter.translate(-y_offset, 0)
            if y > self.height(): break

    def paint_between_tasks(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        painter.setPen(
            QPen(QColor(200, 30, 30, 200), 5) if self.is_today() else QPen(QColor(30, 30, 30, 100), 3)
        )

        arr = sorted(
            [view for view in self.views if view.get_tags().have_to_go() and not view.expired],
            key=lambda x: x.stime)
        if not arr: return

        x = arr[0].x() + arr[0].width() // 2
        view1 = None
        for i, view2 in enumerate(arr):
            if view1 is None:
                same_place = False
                y = int(view2.y() - self.per_hour)
                if y < 0: y = 0

                h, m = 1, 0
                mid = (y + view2.y()) // 2

                painter.drawLine(view2.x() + 10, y, view2.x() + view2.width() - 10, y)
            else:
                same_place = view1.get_where() == view2.get_where()
                y = view1.y() + view1.height() + 1

                h, m = divmod(int(view2.stime - view1.etime), 60)
                mid = (view1.y() + view1.height() + view2.y()) // 2
            view1 = view2

            margin = 30
            draw_arrow(painter, 15, 70, view2.x() + margin, y, None, view2.y() - 1, arrow1=i != 0)
            draw_arrow(painter, 15, 70, view2.x() + view2.width() - margin, y, None, view2.y() - 1, arrow1=i != 0)


            timestr = f'{h}:{"0" if m < 10 else ""}{m}'

            if not same_place:
                if h == 0: self.set_painter_font(painter, bold=True)

                self.set_painter_font(painter, 11)
                painter.drawText(x - 34, mid + 14, '+переезд')
                if view1 is not None:
                    painter.drawLine(
                        QPointF(view2.x() + 10,                 view2.y() - self.per_hour),
                        QPointF(view2.x() + view2.width() - 10, view2.y() - self.per_hour))

            self.set_painter_font(painter, 20)
            if same_place: painter.drawText(x - 25, mid + 9, timestr)
            else:          painter.drawText(x - 25, mid + 1, timestr)

            self.set_painter_font(painter, bold=False)

    def paint_sleep_reminder(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(30, 30, 30), 3))

        time_needed = 11 * 60

        self.blocked_hour = None
        tomorrow = self.now + timedelta(1)

        min_time = 99999
        for event, stime, etime in self.app.get_scheduled_events_and_time():
            if not event.can_occur(tomorrow) or not event.tags.have_to_go(): continue
            if not event.get_timestamps(tomorrow): continue

            min_time = min(min_time, stime)

        if min_time == 99999: return self.paint_no_sleep_reminder()

        self.set_painter_font(painter, size=20, bold=False)

        time_diff = min_time - time_needed
        if time_diff >= 0:
            if time_diff > 4 * 60: return self.paint_no_sleep_reminder()
            message = str_time(time_diff, leading_zero=True)

            time_diff = 24 * 60 - 10
            x_offset = 32
        else:
            time_diff += 24 * 60

            message = str_time(time_diff, leading_zero=True)
            x_offset = 32

            if time_diff < self.min_hour * 60: return self.paint_no_sleep_reminder()
            if time_diff > self.max_hour * 60: return self.paint_no_sleep_reminder()

        if time_diff < 20 * 60:
            time_diff = 22 * 60
            self.set_painter_font(painter, size=16, italic=True)
            painter.setPen(QPen(QColor(200, 30, 30), 5))

            message  = "Ты уверен?"
            x_offset = 50

        if time_diff / 60 - time_diff // 60 <= 10: self.blocked_hour = time_diff // 60
        if time_diff / 60 - time_diff // 60 >= 50: self.blocked_hour = time_diff // 60 + 1
        y = int((time_diff / 60 - self.min_hour) * self.per_hour) + self.margin

        painter.drawLine(15, y, self.width() - 15, y)
        draw_arrow(painter, 15, 70, self.width() // 2, self.height(), None, y + 5, arrow1=False)

        mid_x = self.width() // 2 - x_offset
        asleep = self.app.cfg.asleeps.get(str(self.now))

        if asleep is None or self.min_hour * 60 < asleep < 20 * 60:
            painter.drawText(mid_x, y - 3, message)
        else:
            painter.drawText(mid_x, y - 23, message)

            painter.setPen(QPen(QColor(100, 30, 30, 100), 2))
            self.set_painter_font(painter, size=16, italic=True)
            painter.drawText(mid_x + 6, y - 4, str_time(asleep, leading_zero=True))

    def paint_no_sleep_reminder(self):
        asleep = self.app.cfg.asleeps.get(str(self.now))
        if asleep is None: return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(100, 30, 30, 100), 2))
        self.set_painter_font(painter, size=16, italic=True)

        mid_x = self.width() // 2 - 32

        painter.drawText(mid_x + 6, self.height() - 5, str_time(asleep, leading_zero=True))

    @staticmethod
    def set_painter_font(painter, size=None, bold=None, italic=None):
        font = painter.font()
        if size   is not None: font.setPointSize(size)
        if bold   is not None: font.setBold(bold)
        if italic is not None: font.setItalic(italic)
        painter.setFont(font)

    def paint_current_time_line(self):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        i_diff = (self.app.get_now().date() - self.now).days
        if abs(i_diff) > 1: return

        now = self.app.get_now()
        alpha = 50
        if   now.hour < self.min_hour: y = self.margin // 4
        elif now.hour > self.max_hour: y = self.height() - self.margin // 4
        else:
            hours_from_start = now.hour - self.min_hour + now.minute / 60
            y = int(hours_from_start * self.per_hour) + self.margin
            alpha = 255

        x1 = self.width() * i_diff
        x2 = x1 + self.width()

        painter.setPen(QPen(QColor(255, 0, 0, alpha), 3))
        painter.drawLine(x1, y, x2, y)

        painter.setPen(QPen(QColor(255, 0, 0, alpha), 5))
        painter.drawPolygon([QPoint(x1-5, y+5), QPoint(x1-5, y-5), QPoint(x1, y)])
        painter.drawPolygon([QPoint(x2+5, y+5), QPoint(x2+5, y-5), QPoint(x2, y)])


# ===============================


class SettingsForm(QFrame):
    def __init__(self, main_window):
        super().__init__()

        self.main_window: MainWindow = main_window
        set_size_prop(app, self, 0.7, 0.6)

        self.setWindowTitle("Настройки")
        self.setStyleSheet("""
            QWidget {
                background-color: #E1E1E1;
                color: #000000;
            }
        """)

        self.main_layout = QHBoxLayout()
        self.setLayout(self.main_layout)

        self.side_layout, self.view_layout = sidebars_layout(self.main_layout, title="Настройки")

        self.tabs = {}
        self.side_buttons = []
        for category_name, widget in sidebars_ui(self.side_buttons, self.open_tab, {
            'Общие': [
                [QVBoxLayout, self.create_info_ui]
            ],
            'Тест': [
                [QVBoxLayout, self.create_test_ui]
            ]
        }):
            self.tabs.setdefault(category_name, [])
            self.tabs[category_name].append(widget)
            self.view_layout.addWidget(widget)
        self.open_tab(tuple(self.tabs.keys())[0])

        for button in self.side_buttons:
            self.side_layout.addWidget(button)

        self.error_label = simple_label("", 20)
        self.error_label.setStyleSheet("color: red")
        self.error_label.setHidden(True)
        self.error_label.setWordWrap(True)

        self.test_lb = ErrorArrowDrawer(self)
        self.test_lb.setGeometry(0, 0, 750, 100)
        self.test_lb.raise_()

        self.error_elements: list[QWidget] = []
        self.error_styles = []

        self.error_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.error_timer.timeout.connect(self.hide_error)

        self.side_layout.addStretch(0)
        self.side_layout.addWidget(self.error_label)
        self.side_layout.addWidget(simple_button("Сохранить", "calibri", 20,
                                                 color_scheme='green', callback=self.save_settings))
        self.side_layout.addWidget(simple_button("Отмена",    "calibri", 20,
                                                 color_scheme='red',   callback=self.close))

    def open_tab(self, tab_name):
        for button in self.side_buttons:
            set_color_scheme(button, 'blue' if button.text() == tab_name else 'gray')

        for category_name, elements in self.tabs.items():
            for element in elements:
                element.setVisible(category_name == tab_name)

    def display_error(self, message):
        self.error_label.setText(message)
        self.error_label.setVisible(True)
        self.error_label.setFocus()

        self.error_timer.stop()
        self.error_timer.start(int(max(1000, min(5000, len(message) * 100))))

        self.test_lb.aim_to(self.error_label.pos() + QPoint(self.error_label.width() // 2, -10),
                            self.error_elements, self)

    def hide_error(self):
        self.error_label.setVisible(False)
        self.error_elements.clear()

    def save_settings(self):
        try:
            self.apply_changes(do_write=False)
        except InvalidSettingException as invalid_setting:
            widgets = invalid_setting.widgets
            if not all(widget.isVisible() for widget in widgets):
                for tab in self.tabs:
                    self.open_tab(tab)
                    if not all(widget.isVisible() for widget in widgets): continue
                    # что мб будет
                    break
            self.error_elements = list(widgets)
            self.display_error(invalid_setting.message)
            print(invalid_setting)
        else:
            print("Looks good...")
            self.apply_changes(do_write=True)

    def apply_changes(self, do_write):
        for row in self.period_rows:
            row.get_time_period()
            if do_write: print("Changes saved")

    def create_info_ui(self, layout: QVBoxLayout):
        layout.addWidget(simple_label("Периоды:", 30))

        self.periods_container = QWidget()
        periods_main_layout = QVBoxLayout(self.periods_container)
        periods_main_layout.setContentsMargins(0, 0, 0, 0)

        self.period_scroll = QScrollArea()
        self.period_scroll.setWidgetResizable(True)
        self.period_scroll.setStyleSheet("""
            QScrollArea {
                border: 2px solid black;
                background: white;
            }
        """)
        self.period_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.periods_widget = QWidget()
        self.periods_layout = QVBoxLayout(self.periods_widget)
        self.periods_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.periods_layout.setSpacing(2)
        self.periods_layout.setContentsMargins(5, 5, 5, 5)

        self.period_scroll.setWidget(self.periods_widget)
        periods_main_layout.addWidget(self.period_scroll)

        self.add_btn = icon_button(
            "add.svg", 50, 70, 'green',
            callback=self.add_period_row
        )
        periods_main_layout.addWidget(self.add_btn, 0, Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.periods_container)
        self.period_rows: list[TimePeriodSelector] = []
        self.add_period_row()

    def create_test_ui(self, layout: QVBoxLayout):
        for i in range(100):
            layout.addWidget(simple_label("Секреты", 30))

    def add_period_row(self):
        selector = TimePeriodSelector(self.main_window, self.remove_period_row)
        self.periods_layout.addWidget(selector)
        self.period_rows.append(selector)

    def remove_period_row(self, row_widget):
        for i in reversed(range(self.periods_layout.count())):
            widget = self.periods_layout.itemAt(i).widget()
            if widget == row_widget:
                widget.deleteLater()
                self.period_rows = [r for r in self.period_rows if r != row_widget]
                break

    def resizeEvent(self, a0):
        self.test_lb.setGeometry(0, 0, self.width(), self.height())

class TaskForm(QFrame):
    def open_tab(self, tab_name):
        for button in self.side_buttons:
            set_color_scheme(button, 'blue' if button.text() == tab_name else 'gray')

        for category_name, elements in self.tabs.items():
            for element in elements:
                element.setVisible(category_name == tab_name)

    def __init__(self, main_window, to_edit: ScheduleEvent = None, when = None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.main_window: MainWindow = main_window

        self.now = when or self.main_window.get_now()
        self.edit_target = None if to_edit is None else to_edit

        set_size_prop(app, self, 0.7, 0.6)
        self.setWindowTitle("Добавление задачи" if to_edit is None else "Редактирование задачи")
        self.setStyleSheet("""
            background-color: #E1E1E1;
            color: #000000;
        """)
        self.clicks = 0

        self.main_layout = QHBoxLayout()
        self.side_layout, self.view_layout = sidebars_layout(self.main_layout, title="Настройки")

        self.tabs = {}
        self.side_buttons = []

        for category_name, widget in sidebars_ui(self.side_buttons, self.open_tab, {
            'Имя и описание': [
                [QVBoxLayout, self.create_ui_task_name],
                [QVBoxLayout, self.create_ui_task_desc]
            ],
            'Настройка времени': [
                [QVBoxLayout, self.create_ui_date_selector],
                [QHBoxLayout, self.create_ui_anchor_date]
            ],
            'Выполнение и отмена': [
                [QHBoxLayout, self.create_ui_complete_count],
                [QVBoxLayout, self.create_ui_canceled_dates]
            ],
            'Запланированные задачи': [
                [QVBoxLayout, self.create_ui_announced_tasks]
            ],
            'Прочее': [
                [QVBoxLayout, self.create_ui_tag_select],
                [QVBoxLayout, self.create_ui_color_select]
            ],
            '-': [
                [QVBoxLayout, self.create_ui_finish_buttons]
            ]
        }):
            # self.main_layout.addWidget(widget)
            self.tabs.setdefault(category_name, [])
            self.tabs[category_name].append(widget)
            self.view_layout.addWidget(widget)

        for button in self.side_buttons:
            self.side_layout.addWidget(button)

        if to_edit: self.load_task(to_edit)

        self.main_scroll = QScrollArea(self)
        self.main_scroll.setWidgetResizable(True)
        self.main_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        form_widget = QWidget()
        form_widget.setLayout(self.main_layout)
        self.main_scroll.setWidget(form_widget)

        self.main_layout.setSpacing(5)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(lambda: self.error_message.setHidden(True))

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        offset = 10
        self.main_scroll.move(offset, offset)
        self.main_scroll.setFixedSize(self.width() - offset * 2, self.height() - offset * 2)

    def add_date_option(self, option=None):
        if isinstance(option, DateSelector): option.update_shape()
        self.date_list_layout.addWidget(option or DateSelector(self))
        self.update_date_options()

    def update_date_options(self):
        all_selectors = tuple(self.get_all_date_selectors())
        if all_selectors:
            all_collapsed = all(map(lambda e: not e.visibility, all_selectors))  # all_selectors[0].minimumHeight()
            self.date_scroll_area.setMinimumHeight(300 if all_collapsed else 715)
            for i, e in enumerate(all_selectors):
                e.set_index(i)
        else:
            self.date_scroll_area.setMinimumHeight(200)

    def get_all_date_selectors(self):
        for i in range(self.date_list_layout.count()):
            item = self.date_list_layout.itemAt(i)
            if item is None: continue
            w = item.widget()
            if isinstance(w, DateSelector) and not w.deleted: yield w

    def update_complete_count(self, new_count):
        if new_count < 0: new_count = 0
        self.complete_count = new_count

        self.lb_complete_count.setText(f' {new_count} ' if new_count > 0 else "∞")
        set_color_scheme(self.btn_complete_remove, 'gray' if new_count == 0 else 'red')

    def update_anchor_day(self, new_day, clamp_top=False):
        month_days = calendar.monthrange(self.main_window.get_now().year, self.anchor_month)[1]
        if clamp_top: new_day = min(new_day, month_days)
        if new_day <= 0: new_day += month_days
        new_day = (new_day - 1) % month_days + 1
        self.anchor_day = new_day

        self.lb_anchor_day.setText(f' {new_day} ')

    def update_anchor_month(self, new_month, new_day=None):
        if new_month <= 0: new_month += 12
        new_month = (new_month - 1) % 12 + 1
        self.anchor_month = new_month

        self.lb_anchor_month.setText(f' {months[new_month-1][0].capitalize()} ')
        self.update_anchor_day(new_day or self.anchor_day, clamp_top=True)

    def set_cancel_now(self):
        self.input_add_cancel_date.setText(f'{self.now.day}.{self.now.month}.{self.now.year}')

    def add_cancel_date(self, cancel_date: CancelDate = None, ignore_match=False):
        t = self.input_add_cancel_date.text()
        if not CancelDate.is_valid(t) and not ignore_match: return
        d = cancel_date or CancelDate(self, t)
        if d in self.canceled_dates_values: return
        self.canceled_dates_values.append(d)
        self.canceled_dates_layout.addWidget(d)
        self.update_canceled_dates()

    def remove_cancel_date(self, d: CancelDate):
        self.canceled_dates_values.remove(d)
        self.update_canceled_dates()
        d.deleted = True
        d.deleteLater()

    def move_up_cancel_date(self, d: CancelDate):
        self.canceled_dates_values.remove(d)
        self.canceled_dates_values.insert(0, d)

        self.canceled_dates_layout.removeWidget(d)
        self.canceled_dates_layout.insertWidget(0, d)

        self.update_canceled_dates()

    def update_canceled_dates(self):
        for i, d in enumerate(self.canceled_dates_values, start=1):
            d.set_number(i)

    def add_announced_task(self, v=None):
        self.announced_task_layout.addWidget(AnnouncedTaskSetup(v or self.combo_announced_task.currentTask()))

    def get_tags(self):
        tag_list = TagList()
        for first_btn in self.first_tag_btns:
            for tag_btn in first_btn.other_btns:
                if tag_btn.active:
                    tag_list.add(tag_btn.tag)
        return tag_list

    def update_color(self, new_color_hsv, i=None):
        if i is not None: self.color_value[i] = new_color_hsv
        else:
            self.color_value = new_color_hsv
            self.slider_hue.setValue(new_color_hsv[0])
            self.slider_sat.setValue(new_color_hsv[1])
            self.slider_val.setValue(new_color_hsv[2])

        h, s, v = self.color_value
        col1 = rgb_to_hex(QColor.fromHsv(h, s, v).getRgb())
        col2 = rgb_to_hex(QColor.fromHsv(h, s, min(v+40, 255)).getRgb())
        col3 = rgb_to_hex(QColor.fromHsv(h, s, max(v-40, 0)).getRgb())
        col4 = rgb_to_hex(QColor.fromHsv(h, s, max(v-20, 0)).getRgb())

        self.color_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #{col1};
                border-radius: 10px;
                border: 5px solid #{col4};
                color: #f0f0f0;
            }}
            QPushButton::hover {{
                background-color: #{col2};
                color: #fff;
            }}
            QPushButton::pressed {{
                border: 5px solid #{col3};
                background-color: #{col4};
                color: #eee;
            }}
        """)

    def copy_color(self):
        app.clipboard().setText(rgb_to_hex(QColor.fromHsv(*self.color_value).getRgb()))

    def paste_color(self):
        content = app.clipboard().text().strip("#")
        if len(content) != 6: return

        r = int(content[0:2], 16)
        g = int(content[2:4], 16)
        b = int(content[4:6], 16)

        h, s, v, _ = QColor(r, g, b).getHsv()

        self.update_color([h, s, v])

    def create_ui_task_name(self, layout: QVBoxLayout):
        layout.addWidget(simple_label("Название задачи", 30))

        self.input_name = simple_line_input("Мои (не)любимые занятия", 20, italic=True)
        layout.addWidget(self.input_name)

    def create_ui_task_desc(self, layout: QVBoxLayout):
        layout.addWidget(simple_label("Описание задачи", 30))

        self.input_desc = simple_text_input("Необязательное поле", 20, italic=True)
        layout.addWidget(self.input_desc)

    def create_ui_date_selector(self, layout):
        layout.addWidget(simple_label("Выбор времени", 30))

        self.date_scroll_area = QScrollArea()
        self.date_scroll_area.setWidgetResizable(True)
        self.date_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.date_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.date_list_layout = QVBoxLayout()
        self.date_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.date_list_layout.setContentsMargins(0, 0, 0, 0)
        self.date_list_layout.setSpacing(0)

        self.date_list_widget = QWidget()
        self.date_list_widget.setLayout(self.date_list_layout)
        self.date_list_widget.setObjectName("dateSelectorBorder")
        self.date_list_widget.setStyleSheet(
            "#dateSelectorBorder { border: 4px solid black; }"
        )

        self.date_scroll_area.setWidget(self.date_list_widget)
        layout.addWidget(self.date_scroll_area)

        self.update_date_options()

        layout.addWidget(
            icon_button("add.svg", 50, 70, 'green', callback=self.add_date_option))

    def create_ui_complete_count(self, layout):
        self.lb_complete_count = simple_label(" ? ", 30, "calibri", bold=True)
        self.lb_complete_count.setFixedWidth(40)

        self.btn_complete_remove = icon_button("left.svg",  50, 70, 'gray',
                                               callback=lambda: self.update_complete_count(self.complete_count - 1))
        self.btn_complete_add    = icon_button("right.svg", 50, 70, 'green',
                                               callback=lambda: self.update_complete_count(self.complete_count + 1))
        self.update_complete_count(0)

        layout.addWidget(simple_label("Можно выполнить (раз):", 25))
        layout.addStretch(0)
        layout.addWidget(self.btn_complete_remove)
        layout.addWidget(self.lb_complete_count)
        layout.addWidget(self.btn_complete_add)

    def create_ui_anchor_date(self, layout: QHBoxLayout):
        self.lb_anchor_day   = simple_label("?", 25, fixed_width=35)
        self.lb_anchor_month = simple_label("?", 25, fixed_width=130)

        self.update_anchor_month(
            self.main_window.get_now().month,
            self.main_window.get_now().day
        )

        layout.addWidget(icon_button(
            "calendar.svg", 50, 70, 'yellow',
            callback=lambda: self.update_anchor_month(
                self.main_window.get_now().month,
                self.main_window.get_now().day
            ),
            icon_color=(0, 0, 0)
        ))
        layout.addStretch(1)
        layout.addWidget(simple_label("Дата создания:", 25))
        layout.addStretch(1)
        layout.addWidget(icon_button(
            "down.svg", 25, 30, 'red',
            callback=lambda: self.update_anchor_day(self.anchor_day - 1)
        ))
        layout.addWidget(self.lb_anchor_day)
        layout.addWidget(icon_button(
            "up.svg",   25, 30, 'green',
            callback=lambda: self.update_anchor_day(self.anchor_day + 1)
        ))
        layout.addStretch(1)
        layout.addWidget(icon_button(
            "down.svg", 25, 30, 'red',
            callback=lambda: self.update_anchor_month(self.anchor_month - 1)
        ))
        layout.addWidget(self.lb_anchor_month)
        layout.addWidget(icon_button(
            "up.svg",   25, 30, 'green',
            callback=lambda: self.update_anchor_month(self.anchor_month + 1)
        ))

    def create_ui_canceled_dates(self, layout: QVBoxLayout):
        layout.addWidget(simple_label("Даты отмены", 30))

        self.canceled_dates_values: list[CancelDate] = []
        self.canceled_dates_layout = QVBoxLayout()

        layout.setContentsMargins(10, 0, 10, 10)
        layout.addLayout(self.canceled_dates_layout)

        self.input_add_cancel_date = simple_line_input("ДЕНЬ.МЕСЯЦ.ГОД", 20)
        self.set_cancel_now()

        add_date_layout = QHBoxLayout()
        add_date_layout.addWidget(icon_button("calendar.svg", 50, 70,
                                              'yellow', icon_color=(0, 0, 0),
                                              callback=self.set_cancel_now))
        add_date_layout.addWidget(self.input_add_cancel_date)
        add_date_layout.addWidget(icon_button("add.svg", 50, 70, 'green',
                                              callback=self.add_cancel_date))
        layout.addLayout(add_date_layout)

    def create_ui_announced_tasks(self, layout: QVBoxLayout):
        layout.addWidget(simple_label("Выполняемые действия", 30))

        self.announced_task_layout = QVBoxLayout()
        self.combo_announced_task = AnnouncedTaskSelect()

        add_task_layout = QHBoxLayout()
        add_task_layout.addWidget(self.combo_announced_task)
        add_task_layout.addWidget(icon_button("add.svg", 50, 70, 'green',
                                              callback=self.add_announced_task))

        layout.addLayout(self.announced_task_layout)
        layout.addLayout(add_task_layout)

    def create_ui_tag_select(self, layout: QVBoxLayout):
        self.first_tag_btns = []

        layout.addWidget(simple_label("Выбор тэгов", 35))
        layout.addWidget(new_separator(h=4))
        for tag_group, tags in Tags.dict_like().items():
            layout.addSpacing(10)

            btn_layout = QGridLayout()
            btns = []
            for i, e in enumerate(tags):
                index = i+1 if len(tags) == 2 else i
                btn = TagSelectButton(e, btns)
                btn_layout.addWidget(btn, index // 3, index % 3)
                btns.append(btn)
                if i == 0: self.first_tag_btns.append(btn)

            if len(tags) == 2:
                btn_layout.addWidget(simple_label(f'{tag_group.name}:', 25), 0, 0)
                layout.addLayout(btn_layout)
                for btn in btns: btn.setFixedWidth(100)
            else:
                layout.addWidget(simple_label(tag_group.name, 25))
                layout.addLayout(btn_layout)
            layout.addSpacing(10)
            layout.addWidget(new_separator(h=4))

    def create_ui_color_select(self, layout: QVBoxLayout):
        self.color_btn = QPushButton()
        self.color_btn.setFixedHeight(50)
        set_color_scheme(self.color_btn, 'yellow')

        l1, self.slider_hue = color_select_slider("HUE", 40, 0, 360,
                                                  callback=lambda x: self.update_color(x, 0))
        l2, self.slider_sat = color_select_slider("SAT", 40, 0, 255,
                                                  callback=lambda x: self.update_color(x, 1))
        l3, self.slider_val = color_select_slider("VAL", 40, 0, 255,
                                                  callback=lambda x: self.update_color(x, 2))

        self.update_color([randint(0, 360), randint(200, 255), randint(200, 255)])

        sub_layout = QHBoxLayout()
        sub_layout.addWidget(icon_button("pick.svg",  50, 70, 'yellow', icon_color=(0, 0, 0),
                                         callback=self.copy_color))
        sub_layout.addWidget(self.color_btn)
        sub_layout.addWidget(icon_button("brush.svg", 50, 70, 'yellow', icon_color=(0, 0, 0),
                                         callback=self.paste_color))

        layout.addWidget(simple_label("Выбор цвета", 35))
        layout.addLayout(l1)
        layout.addLayout(l2)
        layout.addLayout(l3)
        layout.addLayout(sub_layout)

    def create_ui_finish_buttons(self, layout: QVBoxLayout):
        btns_layout = QHBoxLayout()
        for i, (text1, text2, color, callback) in enumerate([
            ["Сохранить", "Добавить", 'green', self.finish],
            ["Удалить",   "Отмена",   'red',   self.cancel]
        ]):
            btn = simple_button(text1 if self.edit_target else text2, "calibri", 30, None, color,
                callback=callback)
            btn.setFixedSize(250, 50)
            btns_layout.addWidget(btn)
            if i == 0: btns_layout.addStretch(1)

        self.error_message = simple_label("", 25)
        self.error_message.setStyleSheet(" color: red; ")
        self.error_message.setMinimumHeight(50)
        self.error_message.setWordWrap(True)
        self.error_message.setHidden(True)

        layout.addWidget(self.error_message)
        layout.addLayout(btns_layout)

    def display_error(self, message: str):
        self.error_message.setVisible(True)
        self.error_message.setText(message)
        self.error_message.setFocus()

        self.timer.stop()
        self.timer.start(int(max(1000, min(5000, len(message) * 100))))

    def load_task(self, task: ScheduleEvent):
        self.input_name.setText(task.name)
        self.input_desc.setText(task.desc or "")

        for state in task.date.get_states():
            selector = DateSelector(self)

            if state.get('dayM'): selector.set_to_monthday()

            selector.setup_values(state.get('dayW'), state.get('dayM'), state.get('mon'),
                                  state.get('year'), state.get('periods'))
            selector.set_parity(state.get('parity'))

            selector.time_selector.set_min(state['time'][0])
            selector.time_selector.set_max(state['time'][1])

            self.add_date_option(selector)

        self.update_complete_count(task.times)

        self.update_anchor_month(task.anchor_date.month, task.anchor_date.day)

        # Даты отмены
        for cancel_date in task.canceled_dates:
            self.add_cancel_date(CancelDate(self, f'{cancel_date.day}.{cancel_date.month}.{cancel_date.year}'),
                                 ignore_match=True)

        # Задачи
        for announced_task in task.tasks:
            self.add_announced_task(announced_task)

        # Тэги
        for first_btn in self.first_tag_btns:
            for tag_btn in first_btn.other_btns:
                if tag_btn.tag in task.tags:
                    tag_btn.onClick()

        # Цвет
        col = QColor(*task.color)
        self.update_color([col.hue(), col.saturation(), col.value()])

    def save_task(self):
        assert self.input_name.text(), 'Имя задачи должно быть указано!'

        date = MultiDate()
        for e in self.get_all_date_selectors():
            e.add_multidate_state(date)

        assert date.get_states(), 'Укажи временные промежутки!'

        color = QColor.fromHsv(*self.color_value).getRgb()

        tasks = []
        for i in range(self.announced_task_layout.count()):
            w = self.announced_task_layout.itemAt(i).widget()
            if not isinstance(w, AnnouncedTaskSetup): continue
            tasks.append(w.build_task())


        return ScheduleEvent(
            self.input_name.text(), date,
            description    = self.input_desc.toPlainText() or None,
            times          = self.complete_count,
            anchor_date    = datetime(self.main_window.get_now().year, self.anchor_month, self.anchor_day),
            canceled_dates = [cancel_date.date for cancel_date in self.canceled_dates_values],
            tags           = self.get_tags(),
            color          = [color[0], color[1], color[2]],
            tasks          = tasks
        )

    def finish(self):
        try:
            assert self.edit_target is not None or self.input_name.text() not in self.main_window.scheduled_events,\
                'Такая задача уже существует'
            task = self.save_task()
        except AssertionError as ex:
            self.display_error(str(ex))
            return

        self.main_window.add_new_task(task, self.edit_target)
        self.close()

    def cancel(self):
        if self.edit_target: self.main_window.remove_task(self.edit_target)
        self.close()

    def all_slide_buttons(self):
        for i in range(self.date_list_layout.count()):
            item = self.date_list_layout.itemAt(i)
            if item is None: continue
            widget = item.widget()
            if not isinstance(widget, DateSelector): continue
            for button in widget.weekdays_btns:  yield button
            for button in widget.monthdays_btns: yield button
            for button in widget.months_btns:    yield button
            for button in widget.years_btns:     yield button
            for button in widget.periods_btns:   yield button

    def mouseMoveEvent(self, a0):
        super().mouseMoveEvent(a0)
        for button in self.all_slide_buttons(): button.updateOnMouse(a0)

    def mouseReleaseEvent(self, a0):
        super().mouseReleaseEvent(a0)
        self.clicks = (self.clicks + 1) % 1_000_000

    def keyPressEvent(self, a0):
        k = a0.nativeVirtualKey()
        if k == 13:  # ENTER
            self.finish()


class MainWindow(QMainWindow):
    def __init__(self, debug=False, mock_time=False):
        super().__init__()

        self.loaded = False
        self.cfg = Config.load()

        threading.Thread(target=app_killer_thread, args=(self, self.cfg,)).start()

        self.display_mode = self.cfg.disp_mode
        self.list_mode_match = {}

        self.start_date = datetime.now()

        self.debug     = debug
        self.mock_time = mock_time

        self.setWindowTitle("Приложение")
        self.setGeometry(100, 60, 1000, 600)
        self.setWindowIcon(QIcon("icons/app.svg"))

        self.font_skolar = load_font("Skolar PE Variable Regular.ttf")
        self.day_offset = -self.get_now().weekday()

        self.views_height = self.cfg.view_scale

        self.setStyleSheet("background-color: #FFFFFF;")

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.time_columns: list[TimeColumnView] = []
        self.scheduled_events: list[ScheduleEvent] = list(self.cfg.events)

        self.create_ui_calendar()
        self.create_ui_schedule_view()
        self.create_ui_settings()

        self.task_form = None
        self.settings_form = None

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)

        self.upcoming_events = UpcomingEvents(self, is_hidden=self.cfg.upcoming_hidden)

        self.hide_btn = self.create_button("hide.svg", icon_size=100, callback=self.toggle_toolbar)
        self.hide_btn.setParent(self)

        self.events_list = EventSelector(self)

        self.create_tray()

        self.announce_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.announce_timer.timeout.connect(self.announcements_checker)
        self.announce_timer.start(10 if self.mock_time else 1000)

        self.fell_asleep_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.fell_asleep_timer.timeout.connect(self.asleeps_checker)
        if not self.mock_time:
            self.fell_asleep_timer.start(10_000)

        self.update_schedule_view()
        self.loaded = True

    def get_now(self):
        if not self.mock_time: return datetime.now()

        n = datetime.now()
        return datetime(n.year, 12, 3, 8) + (datetime.now() - self.start_date) * 3000

    def announcements_checker(self):
        now = self.get_now()
        for event in self.scheduled_events:
            event.exec_announced(now)

    def asleeps_checker(self):
        now = datetime.now()
        day = (now - timedelta(hours=TimeColumnView.min_hour)).date()
        minutes = now.time().hour * 60 + now.time().minute

        self.cfg.asleeps[str(day)] = minutes
        self.cfg.save(to_file=False)

    def create_tray(self):
        self.tray_icon = QSystemTrayIcon(self)

        self.tray_icon.setIcon(recolor_icon("list.svg", QColor(255, 255, 255), 30))
        self.tray_icon.setVisible(True)

        # noinspection PyUnresolvedReferences
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

        tray_menu = QMenu()

        tray_menu.addAction(simple_tray_action(self, "Открыть", callback=self.show))
        tray_menu.addSeparator()
        tray_menu.addAction(simple_tray_action(self, "Закрыть", callback=app.quit, enabled=True))

        self.tray_icon.setContextMenu(tray_menu)

    def on_tray_icon_activated(self, reason: QSystemTrayIcon.ActivationReason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.show()

    def have_tray(self):
        return not self.tray_icon.icon().isNull()

    def create_ui_calendar(self):
        self.days_frame = QFrame()
        self.days_frame.setStyleSheet("background-color: #E0E0E0; border-bottom: 2px solid black")
        self.days_frame.setFixedHeight(120)

        self.calendar_days_layout = QHBoxLayout()
        self.calendar_days_layout.setContentsMargins(10, 0, 10, 0)
        self.calendar_days_layout.setSpacing(0)

        self.days_frame.setLayout(self.calendar_days_layout)

        self.main_layout.addWidget(self.days_frame)

    def create_ui_schedule_view(self):
        self.schedule_view = QWidget()
        layout = QHBoxLayout(self.schedule_view)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        now = self.get_now().date()
        counter = now - timedelta(now.weekday() + self.day_offset)

        for i in range(7):
            fr = TimeColumnView(self, i, counter)
            counter += timedelta(1)
            layout.addWidget(fr)
            self.time_columns.append(fr)

        self.schedule_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self.schedule_scroll = QScrollArea()
        self.schedule_scroll.setWidget(self.schedule_view)
        self.schedule_scroll.setWidgetResizable(True)
        self.schedule_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.schedule_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.schedule_scroll.verticalScrollBar().setValue(self.cfg.y_view)

        self.main_layout.addWidget(self.schedule_scroll)

    def create_ui_settings(self):
        self.settings_frame = QFrame()
        self.settings_frame.setFixedHeight(100)
        self.settings_frame.setStyleSheet("background-color: #E0E0E0; border-top: 2px solid black")

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 0, 10, 0)
        button_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.btn_events_list = self.create_button("list.svg", callback=self.show_events_list)

        button_layout.addWidget(self.create_button("gear.svg", callback=self.show_settings_menu))
        button_layout.addWidget(self.btn_events_list)

        button_layout.addWidget(self.create_button("telescope.svg", callback=self.display_cycle_button))

        button_layout.addWidget(self.create_button("add.svg", callback=self.create_task_add_form))

        button_layout.addWidget(self.create_button("left.svg",  callback=lambda : self.change_day(-1)))
        button_layout.addWidget(self.create_button("right.svg", callback=lambda : self.change_day(+1)))

        button_layout.addStretch()

        button_layout.addWidget(self.create_button("photo.svg", callback=self.make_screenshot))
        button_layout.addSpacing(85)

        self.settings_frame.setLayout(button_layout)
        self.main_layout.addWidget(self.settings_frame)

    # noinspection PyUnresolvedReferences
    @staticmethod
    def create_button(icon_path, icon_size=110, callback=None):
        button = QPushButton()
        button.setIcon(QIcon("icons/" + icon_path))
        button.setIconSize(QSize(icon_size, icon_size))
        button.setFixedSize(80, 80)
        button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                background-color: #CCCCCC;  /* Светло-серый фон при наведении */
            }
            QPushButton:pressed {
                background-color: #AAAAAA;  /* Темнее при нажатии */
                            }
        """)

        animation = QPropertyAnimation(button, b"iconSize")

        def template(easing, start, end, duration=250, addition=None):
            if addition: addition()

            animation.setStartValue(QSize(start, start))
            animation.setEndValue(QSize(end, end))
            animation.setEasingCurve(easing)
            animation.setDuration(duration)
            animation.start()

        button.enterEvent = lambda x: template(QEasingCurve.Type.OutExpo, icon_size,    icon_size+40)
        button.leaveEvent = lambda x: template(QEasingCurve.Type.Linear,  icon_size+40, icon_size, 100)
        button.released.connect(lambda: template(QEasingCurve.Type.InOutQuad, icon_size+20, icon_size+40, 100))
        button.pressed.connect(lambda: template(QEasingCurve.Type.Linear,     icon_size+40, icon_size+20, 0,
                                                addition=callback))

        return button

    def show_settings_menu(self):
        if self.settings_form: self.settings_form.close()
        self.settings_form = SettingsForm(self)
        self.settings_form.show()

    def show_events_list(self):
        if self.events_list.isVisible():
            self.events_list.setHidden(True)
        else:
            self.events_list.set_events(self.scheduled_events)
            self.events_list_update_pos()

    def update_calendar(self):
        for i in range(self.calendar_days_layout.count()):
            w = self.calendar_days_layout.itemAt(i)
            w.widget().deleteLater()

        counter = self.get_now() + timedelta(self.day_offset)
        self.calendar_labels: list[list[QFrame | QLabel | QLabel]] = []

        for i in range(7):
            dayW_label = QLabel(days_of_week[counter.weekday()])
            dayM_label = QLabel(f'{counter.day} {months[counter.month-1][0]}')

            dayW_label.setFont(QFont(self.font_skolar, 50))
            dayW_label.setContentsMargins(0, -20, 0, 0)

            dayM_label.setFont(QFont(self.font_skolar, 18))
            dayM_label.setContentsMargins(0, -40, 0, 0)
            dayM_label.setMinimumWidth(120)

            for day_label in (dayM_label, dayW_label):
                day_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                day_label.setFixedHeight(100)

                day_label.setStyleSheet(
                    f"color: black;"
                    f"background-color: transparent;"
                    "border: none;"
                )

            self.calendar_days_layout.addWidget(new_separator(w=3, h=100))

            temp_frame = QFrame()
            temp_frame.setMinimumSize(0, 0)
            temp_layout = QVBoxLayout()
            temp_layout.addWidget(dayW_label)
            temp_layout.addWidget(dayM_label)

            self.calendar_labels.append([temp_frame, dayW_label, dayM_label])
            temp_frame.setLayout(temp_layout)
            self.calendar_days_layout.addWidget(temp_frame)

            self.calendar_set_style(counter.date(), i, temp_frame)

            counter += timedelta(1)

        self.calendar_days_layout.addWidget(new_separator(w=3, h=100))

    def calendar_set_style(self, day: date, i, frame: QFrame):
        css = {'border-top': '7px solid #22333333'}
        have_important = self.time_columns[i].is_important

        if self.get_now().date() == day:
            css = {'background-color': '#440000ff', 'border-top': '7px solid #440000ff'}
            if have_important:
                css = {'background-color': '#44ff0000', 'border-top': '10px solid #44ff0000'}

        elif have_important:
            css = {'border-top': '7px solid #44ff0000'}

        frame.setStyleSheet(''.join([f'{k}:{v};' for k, v in css.items()]))

    def change_day(self, mul):
        hold_shift = QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier
        self.day_offset += (7 if hold_shift else 1) * mul
        self.update_schedule_view()

    def display_cycle_button(self):
        if QApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier:
            self.display_mode = DisplayModes.cycle(self.display_mode, -1)
        else:
            self.display_mode = DisplayModes.cycle(self.display_mode, +1)
        self.cfg.save(disp_mode=self.display_mode)
        self.update_schedule_view()

    def update_zoom(self, offset):
        if self.display_mode not in [DisplayModes.FIELD]: return
        self.views_height = max(1000, min(3000, self.views_height + offset))
        self.update_schedule_view()

    def create_task_add_form(self, to_edit=None):
        if self.task_form: self.task_form.close()
        self.task_form = TaskForm(self, to_edit)
        self.task_form.show()

    def add_new_task(self, task: ScheduleEvent, to_remove=None):
        if to_remove: self.scheduled_events.remove(to_remove)
        self.scheduled_events.append(task)
        self.update_schedule_view()

        self.cfg.save(events=self.scheduled_events)

    def remove_task(self, to_remove):
        self.scheduled_events.remove(to_remove)
        self.update_schedule_view()

        self.cfg.save(events=self.scheduled_events)

    def get_scheduled_events_and_time(self):
        for time_column in self.time_columns:
            for view in time_column.views:
                yield view.get_event_and_time()

    def toggle_toolbar(self):
        if self.settings_frame.isVisible():
            opacity = 0.3
            path    = "show"
            self.settings_frame.setHidden(True)
            self.hide_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background-color: transparent;  /* Светло-серый фон при наведении */
                }
                QPushButton:pressed {
                    background-color: transparent;  /* Темнее при нажатии */
                                }
            """)
        else:
            opacity = 1
            path    = "hide"
            self.settings_frame.setVisible(True)
            self.hide_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: transparent;
                    border: none;
                }
                QPushButton:hover {
                    background-color: #CCC;  /* Светло-серый фон при наведении */
                }
                QPushButton:pressed {
                    background-color: #AAA;  /* Темнее при нажатии */
                }
            """)

        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(opacity)
        self.hide_btn.setGraphicsEffect(opacity_effect)
        self.hide_btn.setIcon(QIcon(f"icons/{path}.svg"))
        self.events_list_update_pos()

        QTimer().singleShot(1, lambda : self.resize_columns())

    def update_schedule_view(self):
        self.upcoming_events.update_events(self.scheduled_events)

        for event in self.scheduled_events:
            event.connect_app(self)

        if self.display_mode == DisplayModes.LIST:
            self.list_mode_match.clear()
            self.update_columns(do_resize=False)
            max_no = 0
            for column in self.time_columns:
                view_counter = 0
                for view in sorted(column.views, key=lambda x: x.stime):
                    self.list_mode_match[view] = view_counter
                    max_no = max(max_no, view_counter)
                    view_counter += 1
            self.list_mode_match["max_no"] = max_no + 1

        self.update_columns()
        self.update_calendar()

    def update_columns(self, do_resize=True):
        for i, column in enumerate(self.time_columns, start=1):
            column.update_views()
            if do_resize: column.resizeEvent(None)

    def resize_columns(self, a0=None):
        for column in self.time_columns:
            column.resizeEvent(a0)

    def events_list_update_pos(self):
        if self.events_list.isHidden(): return
        self.events_list.move(
            10,
            self.height() - self.events_list.height() - 10
            - (self.settings_frame.height() if self.settings_frame.isVisible() else 0)
        )

    def make_screenshot(self):
        screenshot = self.schedule_view.grab()
        clipboard = QApplication.clipboard()
        clipboard.setPixmap(screenshot)
        self.tray_icon.showMessage(
                "Задачи сохранены в буфер как картинка",
                f"{self.time_columns[0].now.day} - {self.time_columns[-1].now.day} числа",
                QIcon(screenshot.scaled(64, 64, Qt.AspectRatioMode.KeepAspectRatio)),
                5000
            )

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        self.hide_btn.move(
            self.width()  - self.hide_btn.width()  - 10,
            self.height() - self.hide_btn.height() - 10
        )
        self.events_list_update_pos()

        self.upcoming_events.move(
            self.width() - self.upcoming_events.width() - 10
                + (25 if self.upcoming_events.hidden else 0),
            self.days_frame.height() + 10
        )
        self.resize_columns()

    def closeEvent(self, a0):
        self.cfg.save(y_view=self.schedule_scroll.verticalScrollBar().value(),
                      view_scale=self.views_height)
        if not self.debug:
            self.hide()
            a0.ignore()

    def keyPressEvent(self, a0):
        k = a0.nativeVirtualKey()

        if k == Qt.Key.Key_A: self.change_day(-1)
        if k == Qt.Key.Key_D: self.change_day(+1)

        if k == Qt.Key.Key_W: self.update_zoom(-200)
        if k == Qt.Key.Key_S: self.update_zoom(+200)

        if k == Qt.Key.Key_Q: self.show_events_list()
        if k == Qt.Key.Key_E: self.toggle_toolbar()


try:
    print("Settings:", sys.argv[1:])
    if os.getcwd().endswith("output"): os.chdir("..")
    with DebugTimer("App creation"):
        app = SingleInstanceApplication(sys.argv, unique_key="manager_app_homemade")
    with DebugTimer("Window open"):
        window = MainWindow(**{k: True for k in sys.argv[1:]})
    window.show()
    sys.exit(app.exec())
except (SystemExit, KeyboardInterrupt): print("Системный выход")
except:
    exc_type, exc_value, exc_traceback = sys.exc_info()
    print("Возникла ошибка, лог создан")
    try:
        log_error()
    except:
        print("!!!CANNOT CREATE ERROR LOG!!!\n")
        print("TYPE  -", exc_type)
        print("VALUE -", exc_value)
        print("\n\n")
        traceback.print_tb(exc_traceback)
        print("\n\n\n")
        os.system("pause")
    raise
