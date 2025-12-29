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
from typing import Type, Iterable, Callable

from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QTimer, QSharedMemory, QRectF, QPointF, QPropertyAnimation, \
    QEasingCurve
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QFontDatabase, QAction, QStandardItem, \
    QStandardItemModel, QTextOption, QEnterEvent
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QFrame, QGridLayout, QGraphicsDropShadowEffect, QSlider,
    QLineEdit, QVBoxLayout, QScrollArea, QTextEdit, QApplication, QComboBox, QMessageBox, QStyleOptionButton, QStyle,
    QLayout, QBoxLayout, QSpacerItem, QSizePolicy, QGraphicsOpacityEffect
)

from announced_task import AnnouncedTask
from multidate_v2 import MultiDateWeekday, MultiDateMonthday, MultiDateParity, days_of_week, months, EventStamp, \
    str_to_datetime, datetime_to_str, MultiDateMixer, AllTimestampsWrapper, MultiDateEmpty
from tags import Tags, Tag, TagList
from date_utils import ScheduleEvent, rgb_to_hex, str_time, interpolate, beauty_time, \
    MultiDateHolder, beauty_date, is_main_window
from time_periods import all_periods, TimePeriod
from utils import DebugTimer

color_schemes = {
    'yellow': ["#FAE40E", "#FDE912", "#887007", "#C0AE0B"],
    'green':  ["#02D600", "#50F000", "#026200", "#339800"],
    'red':    ["#D72801", "#F63D00", "#601500", "#9B1602"],
    'blue':   ["#0094D8", "#00A4E8", "#004565", "#0063A0"],
    'gray':   ["#9F9F9F", "#AFAFAF", "#3F3F3F", "#6F6F6F"],
    'white':  ["#EDEDE1", "#F0F0F1", "#CDCDC1", "#555"]
}

def set_color_scheme(element, name):
    color_norm, color_hover, color_click, color_border = color_schemes.get(name, (0, 0, 0, 0))
    element.setStyleSheet(f"""
        QPushButton {{
            background-color: {color_norm};
            border-radius: 10px;
            border: 5px solid {color_border};
            color: #f0f0f0;
        }}
        QPushButton::hover {{
            background-color: {color_hover};
            color: #fff;
        }}
        QPushButton::pressed {{
            border: 5px solid {color_click};
            background-color: {color_border};
            color: #eee;
        }}
    """)

def set_custom_color_scheme(element, r, g, b, hover_offset=40, click_offset=-40, border_offset=-20,
                            addition="", element_name="QPushButton", after=""):
    col_rgb = QColor.fromRgb(r, g, b)
    h = col_rgb.hue()
    s = col_rgb.saturation()
    v = col_rgb.value()
    col1 = rgb_to_hex(QColor.fromHsv(h, s, v).getRgb())
    col2 = rgb_to_hex(QColor.fromHsv(h, s, max(0, min(255, v + hover_offset))).getRgb())
    col3 = rgb_to_hex(QColor.fromHsv(h, s, max(0, min(255, v + click_offset))).getRgb())
    col4 = rgb_to_hex(QColor.fromHsv(h, s, max(0, min(255, v + border_offset))).getRgb())

    element.setStyleSheet(f"""
        {element_name} {{
            background-color: #{col1};
            border-radius: 10px;
            border: 5px solid #{col4};
            color: #f0f0f0;
            {addition}
        }}
        {element_name}::hover {{
            background-color: #{col2};
            color: #fff;
            {addition}
        }}
        {element_name}::pressed {{
            border: 5px solid #{col3};
            background-color: #{col4};
            color: #eee;
            {addition}
        }}
        {after}
    """)

def recolor_icon(path, color: QColor, scale=1):
    # Загружаем оригинальный pixmap
    original_pixmap = QPixmap("icons/" + path)

    # Создаем новый pixmap с учетом масштаба
    size = original_pixmap.size() * scale
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)  # Прозрачный фон

    # Рисуем отмасштабированное изображение и применяем цвет
    painter = QPainter(pixmap)
    painter.drawPixmap(0, 0, original_pixmap.scaled(size))  # Масштабируем исходный pixmap
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()

    return QIcon(pixmap)

def simple_label(name, size, font="Calibri", fixed_width=None, bold=False, italic=False):
    lb = QLabel(name)
    lb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    if fixed_width: lb.setFixedWidth(fixed_width)
    f = QFont(font, size)

    f.setBold(bold)
    f.setItalic(italic)

    lb.setFont(f)
    return lb

def simple_button(text, font, font_size, btn_size=None, color_scheme=None, callback=None, bold=False, italic=False):
    btn = QPushButton(text)
    f = QFont(font, font_size)
    f.setBold(bold)
    f.setItalic(italic)
    btn.setFont(f)
    if btn_size: btn.setFixedSize(btn_size, btn_size)

    if color_scheme: set_color_scheme(btn, color_scheme)

    if callback:
        # noinspection PyUnresolvedReferences
        btn.clicked.connect(callback)
    return btn

def simple_line_input(default_text, font_size, font="calibri", bold=False, italic=False):
    font = QFont(font, font_size)
    font.setItalic(italic)
    font.setBold(bold)

    line_edit = QLineEdit()
    line_edit.setFont(font)
    line_edit.setPlaceholderText(default_text)
    line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
    line_edit.setStyleSheet("border-bottom: 3px solid lightblue;")

    return line_edit

def simple_text_input(default_text, font_size, font="calibri", bold=False, italic=False):
    font = QFont(font, font_size)
    font.setItalic(italic)
    font.setBold(bold)

    text_edit = QTextEdit()
    text_edit.setFixedHeight(110)
    text_edit.verticalScrollBar().setHidden(True)
    text_edit.setFont(font)
    text_edit.setPlaceholderText(default_text)
    text_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)
    text_edit.setStyleSheet("border-bottom: 3px solid lightblue;")

    return text_edit

def simple_combo_box(options, font_size, font="calibri", bold=False, italic=False):
    font = QFont(font, font_size)
    font.setItalic(italic)
    font.setBold(bold)

    box = QComboBox()
    box.setFont(font)
    box.setStyleSheet("border-bottom: 3px solid lightblue;")

    if options: box.addItems(options)

    return box

def simple_tray_action(parent, name, callback=None, enabled=True):
    action = QAction(name, parent)

    if callback: # noinspection PyUnresolvedReferences
        action.triggered.connect(callback)
    action.setEnabled(enabled)
    return action

def simple_line_edit(placeholder=None, font_size=20, font="Anonymous Pro", multi_line=False,
                     on_text_edit=None, bold=False, italic=False):
    edit = AutoExpandingTextEdit(70) if multi_line else QLineEdit()

    if not multi_line:
        edit.setFixedHeight(40)
        edit.setAlignment(Qt.AlignmentFlag.AlignCenter)

    if placeholder is not None:
        edit.setPlaceholderText(placeholder)

    if on_text_edit is not None:
        edit.textChanged.connect(on_text_edit)

    font = QFont(font, font_size)
    font.setItalic(italic)
    font.setBold(bold)
    edit.setFont(font)

    return edit

def color_select_slider(text, size, min_, max_, callback=None, font="calibri"):
    layout = QHBoxLayout()

    slider = ColorSelectSlider(min_, max_, callback)

    layout.addWidget(simple_label(text, size, font=font))
    layout.addStretch(1)
    layout.addWidget(slider)
    return layout, slider

def icon_button(icon_path, btn_size, icon_size, color_scheme, callback=None, icon_color=None, parent=None):
    btn = QPushButton() if parent is None else QPushButton(parent)
    if btn_size: btn.setFixedSize(btn_size, btn_size)

    btn.setIcon(recolor_icon(icon_path, QColor(
        *(icon_color or (240, 240, 240))
    )))
    btn.setIconSize(QSize(icon_size, icon_size))

    color_norm, color_hover, color_click, color_border = color_schemes.get(color_scheme, (0, 0, 0, 0))
    btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {color_norm};
            border-radius: 10px;
            border: 5px solid {color_border};
        }}
        QPushButton::hover {{
            background-color: {color_hover};
        }}
        QPushButton::pressed {{
            border: 5px solid {color_click};
            background-color: {color_border};
        }}
    """)

    if callback:
        # noinspection PyUnresolvedReferences
        btn.clicked.connect(callback)
    return btn

def load_font(path):
    font_id = QFontDatabase.addApplicationFont(f"fonts/{path}")
    if font_id == -1: return None
    return QFontDatabase.applicationFontFamilies(font_id)[0]

def new_separator(*, w=None, h=None, col="#000000"):
    separator = QFrame()
    if w is not None: separator.setFixedWidth(w)
    if h is not None: separator.setFixedHeight(h)
    separator.setStyleSheet(f"background-color: {col};")
    return separator

def new_slash(size=20, color="black"):
    slash = simple_label("/", size)
    slash.setStyleSheet(f"color: {color}; border: none;")
    return slash

def ui_shadow(element):
    shadow_effect = QGraphicsDropShadowEffect()
    shadow_effect.setBlurRadius(5)
    shadow_effect.setOffset(2, 2)
    shadow_effect.setColor(QColor(0, 0, 0, 160))
    element.setGraphicsEffect(shadow_effect)

def draw_arrow(painter: QPainter, length, arrow_angle, x1, y1, x2=None, y2=None, arrow1=False, arrow2=True):
    if x2 is None: x2 = x1
    if y2 is None: y2 = y1
    angle = -atan2(y2 - y1, x2 - x1)

    painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
    if arrow1:
        painter.drawLine(QPointF(x1, y1),
                         QPointF(x1 + cos(angle + radians(-arrow_angle)) * length,
                                 y1 - sin(angle + radians(-arrow_angle)) * length))
        painter.drawLine(QPointF(x1, y1),
                         QPointF(x1 + cos(angle - radians(-arrow_angle)) * length,
                                 y1 - sin(angle - radians(-arrow_angle)) * length))
    if arrow2:
        painter.drawLine(QPointF(x2, y2),
                         QPointF(x2 + cos(angle + radians(180 - arrow_angle)) * length,
                                 y2 - sin(angle + radians(180 - arrow_angle)) * length))
        painter.drawLine(QPointF(x2, y2),
                         QPointF(x2 + cos(angle - radians(180 - arrow_angle)) * length,
                                 y2 - sin(angle - radians(180 - arrow_angle)) * length))

def paint_highlighted_border(widget: QWidget, frame, color: QColor = None, speed=100, narrow=False, margin=5):
    painter = QPainter(widget)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    thickness = 1 if narrow else 2
    paint_important_border(widget, painter, 0, 0, 0, frame, color, speed, thickness, margin)
    paint_important_border(widget, painter, 1, 1, 0, frame, color, speed, thickness, margin)
    paint_important_border(widget, painter, 1, 0, 1, frame, color, speed, thickness, margin)
    paint_important_border(widget, painter, 0, 1, 1, frame, color, speed, thickness, margin)

    painter.setPen(QPen(QColor(0, 0, 0), 10 if narrow else 14))
    for flip_x, flip_y, angle in [
        [0, 0, 90],
        [0, 1, 180],
        [1, 0, 0],
        [1, 1, 270]
    ]:
        painter.drawArc(widget.width() - 32 if flip_x else 2, widget.height() - 32 if flip_y else 2,
                        30, 30, angle * 16, 90 * 16)

def paint_important_border(widget: QWidget, painter, flip_x, flip_y, flip_anim,
                           frame, color, speed, half_size, margin):
    min_length = 40
    min_margin, max_margin = margin, 20

    h, w = widget.height(), widget.width()
    if flip_y: h, w = w, h

    max_frame = speed
    frac  = ((frame % (max_frame + 2)) - 1) * 2 / max_frame - 1
    frac2 = (((frame + max_frame // 2) % (max_frame + 2)) - 1) * 2 / max_frame - 1

    if flip_anim:
        frac  *= -1
        frac2 *= -1

    allowed_height = h - max_margin * 2
    total = allowed_height // min_length

    for i in range(total):
        y1 = allowed_height * i / total + max_margin
        y2 = allowed_height * (i + 1) / total + max_margin

        if i % 2:
            p1 = int(interpolate(y1, y2, frac))
            p2 = int(interpolate(y1, y2, frac + 1))
        else:
            p1 = int(interpolate(y1, y2, frac2))
            p2 = int(interpolate(y1, y2, frac2 + 1))

        if p1 == p2: continue

        p = w - min_margin if flip_x else min_margin
        if flip_y:
            painter.fillRect(
                p1, p - half_size,
                p2 - p1 + 1, half_size * 2, color
            )
        else:
            painter.fillRect(
                p - half_size, p1,
                half_size * 2, p2 - p1 + 1, color
            )


def framed_ui(parent, structure: dict[str, list[list[Type[QVBoxLayout] | Type[QVBoxLayout]] | list]]):
    for j, (spoiler_name, spoiler_options) in enumerate(structure.items()):
        widgets = []
        have_spoiler = not spoiler_name.startswith('-')
        if have_spoiler:
            spoiler = SpoilerOptions(spoiler_name)
            yield spoiler

        for i, (layout_type, ui_creator) in enumerate(spoiler_options):
            fr = QFrame()
            style = f"""
                background-color: {"#f4f4f4" if i % 2 else "#f9f9f9"};
            """
            radius = 5
            if i == 0:
                style += f"border-top-left-radius:    {radius}px; border-top-right-radius:    {radius}px; "
            if i == len(spoiler_options)-1:
                style += f"border-bottom-left-radius: {radius}px; border-bottom-right-radius: {radius}px; "

            fr.setStyleSheet(style)
            layout: QHBoxLayout = layout_type()
            ui_creator(layout)
            layout.addStretch(0)
            fr.setLayout(layout)

            widgets.append(fr)
            yield fr

        if have_spoiler:
            # noinspection PyUnboundLocalVariable
            spoiler.set_widgets(widgets, parent=parent)

            if j == 0:
                spoiler.set_shown(True)

def sidebars_layout(main_layout: QBoxLayout, side_width=300, title=None):
    side_layout = QVBoxLayout()
    view_layout = QVBoxLayout()

    side_frame = QFrame()
    side_frame.setObjectName("sideFrame")
    side_frame.setStyleSheet("#sideFrame { background: #ddd; border-right: 5px solid black; }")
    side_frame.setFixedWidth(side_width)
    side_frame.setLayout(side_layout)

    main_layout.setContentsMargins(0, 0,  0, 0)
    side_layout.setContentsMargins(0, 0, 10, 0)
    view_layout.setContentsMargins(0, 0,  0, 0)
    main_layout.addWidget(side_frame)
    main_layout.addLayout(view_layout)

    if title: side_layout.addWidget(simple_label(title, 30))
    return side_layout, view_layout


def sidebars_ui(side_buttons: list | QVBoxLayout, opener,
                structure: dict[str, list[list[Type[QVBoxLayout] | Type[QVBoxLayout]] | list]]):
    for j, (category_name, category_options) in enumerate(structure.items()):
        def on_click(_, tab_name=category_name):
            opener(tab_name)
        side_buttons.append(simple_button(category_name, "calibri", 25, color_scheme='gray', callback=on_click))

        scroll = QScrollArea()
        scroll.setContentsMargins(0, 0, 0, 0)
        scroll.setWidgetResizable(True)
        scroll.setObjectName("innerScroll")
        scroll.setStyleSheet("""
            #innerScroll {
                border: 2px solid black;
                background: white;
            }
        """)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        master_layout = QVBoxLayout()

        for i, option in enumerate(category_options):
            if isinstance(option, int):
                master_layout.addStretch(option)
            elif isinstance(option, list):
                layout_type, ui_creator = option
                fr = QFrame()
                layout: QHBoxLayout = layout_type()
                ui_creator(layout)
                layout.setAlignment(Qt.AlignmentFlag.AlignTop)
                fr.setLayout(layout)
                master_layout.addWidget(fr)

        w = QWidget()
        w.setLayout(master_layout)
        scroll.setWidget(w)
        yield category_name, scroll

    opener(tuple(structure.keys())[0])

def set_size_prop(app: QApplication, widget: QWidget, w, h):
    size = app.primaryScreen().size()
    widget.setGeometry(
        int(size.width() * (1 - w) / 2), int(size.height() * (1 - h) / 2),
        int(size.width() * w),           int(size.height() * h)
    )


class LayoutBuilder:
    def __init__(self, type_):
        self.layout: QHBoxLayout | QVBoxLayout | QGridLayout = type_()

    @staticmethod
    def prepare_default_kwargs(stretch = None, alignment = None):
        kwargs = {}
        if stretch   is not None: kwargs["stretch"]   = stretch
        if alignment is not None: kwargs["alignment"] = alignment
        return kwargs

    def addWidget(self, widget: QWidget, stretch = None, alignment = None):
        self.layout.addWidget(widget, **self.prepare_default_kwargs(stretch, alignment))
        return self

    def addLayout(self, layout: QLayout, stretch = None):
        self.layout.addLayout(layout, **self.prepare_default_kwargs(stretch))
        return self

    def addWidgetAt(self, x, y, widget: QWidget, stretch = None, alignment = None):
        self.layout.addWidget(widget, y, x, **self.prepare_default_kwargs(stretch, alignment))
        return self

    def addLayoutAt(self, x, y, layout: QLayout, stretch = None):
        self.layout.addLayout(layout, x, y, **self.prepare_default_kwargs(stretch))
        return self

    def addStretch(self, stretch: int):
        self.layout.addStretch(stretch)
        return self

    def addSpacing(self, spacing: int):
        self.layout.addSpacing(spacing)
        return self

    def build(self, alignment=None, spacing=None):
        if alignment is not None: self.layout.setAlignment(alignment)
        if spacing is not None: self.layout.setSpacing(spacing)
        return self.layout

    def addAllWidgets(self, ws: Iterable[QWidget], **kwargs):
        for w in ws: self.addWidget(w, **kwargs)
        return self


class AutoExpandingTextEdit(QTextEdit):
    def __init__(self, min_height, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.min_height = min_height

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.document().contentsChanged.connect(self.update_height)

        self.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)

    def text(self):
        return self.toPlainText()

    def update_height(self):
        doc_height = self.document().size().height()
        new_height = max(
            int(doc_height) + self.contentsMargins().top() + self.contentsMargins().bottom(),
            self.min_height
        )

        self.setFixedHeight(int(new_height))

    def showEvent(self, event):
        super().showEvent(event)
        self.update_height()


class FormulaEdit(AutoExpandingTextEdit):
    def __init__(self, task_edit: "main.TaskForm", error_display: QLabel, font="Anonymous Pro"):
        super().__init__(40)
        self.setFont(QFont(font, 30))

        self.task_edit = task_edit
        self.error_display = error_display

        self.selectors_count = 0
        self.textChanged.connect(self.validate)

    def update_selectors(self):
        new_selectors = tuple(self.task_edit.get_all_date_selectors())
        self.selectors_count = len(new_selectors)
        if self.selectors_count > 1:
            self.setEnabled(True)
            self.setPlaceholderText(f'({" + ".join(map(chr, range(ord("A"), ord("A") + len(new_selectors))))})')
            self.validate()

            font = self.font()
            font.setItalic(False)
            font.setPointSize(30)
            self.setFont(font)
        else:
            self.setDisabled(True)
            self.setPlaceholderText("Для формулы нужно как минимум 2 условия")
            self.setStyleValid()

            font = self.font()
            font.setItalic(True)
            font.setPointSize(15)
            self.setFont(font)

        self.update_height()


    def setStyleValid(self):
        self.setStyleSheet("""
                    color: black;
                """)
        self.error_display.hide()

    def setStyleInvalid(self, error_msg: str):
        self.setStyleSheet("""
                    color: red;
                """)
        if error_msg:
            self.error_display.setText(error_msg)
            self.error_display.show()
        else:
            self.error_display.hide()

    def validate(self):
        if not self.text(): return self.setStyleValid()
        try:
            # Если в MultiDateParity передать нули в days_on и days_off, то get_all_timestamps
            # не будет расчитывать дни, а просто сразу завершится
            variables = {
                chr(ord('a') + i): AllTimestampsWrapper(MultiDateEmpty(), date(1,1,1), date(1,1,1))
                for i in range(self.selectors_count)
            }
            eval(MultiDateMixer.normalise_formula(self.text()), variables)

        except SyntaxError as ex:
            self.setStyleInvalid(f'Введите формулу полностью\n({ex.offset} ТУТ -> {self.text()[ex.offset-1:ex.offset+1]})')

        except TypeError:
            self.setStyleInvalid('Недопустимая операция')

        except NameError as ex:
            undefined_name = re.search(r"'(.+)'", ex.args[0]).group(0)
            self.setStyleInvalid(f'Неизвестная переменная: {undefined_name}\n'
                                 f'Для ссылок для события вы должны использовать буквы англиского алфавита\n'
                                 f'Для операций: "+", "*", "and", "or", "и", "или"')

        except Exception as ex:
            self.setStyleInvalid(f'Неизвестная ошибка: {ex}\n{type(ex)}')

        else:
            self.setStyleValid()


class InvalidSettingException(Exception):
    def __init__(self, message: str, *widgets: QWidget):
        self.message = message
        self.widgets = widgets

    def __str__(self):
        return f'Ошибка в настройках - "{self.message}"'


class ErrorArrowDrawer(QFrame):
    def __init__(self, parent):
        super().__init__(parent)

        self.setStyleSheet("""
            border: 5px solid #ff000011;
            border-radius: 15px;
            background: transparent;
        """)

        self.arrows: list[SmoothArrow] = []

        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.tick = 0
        self.ticker = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.ticker.timeout.connect(self._tick_arrows)
        self.ticker.start(60 // 1000)

    def aim_to(self, from_point: QPoint, widgets: list[QWidget], mapping=None):
        created_arrows = len(self.arrows)

        for i, arrow in enumerate(self.arrows):
            arrow.aim_to(from_point, widgets[i])
            arrow.refresh()

        for i in range(created_arrows, len(widgets)):
            self.arrows.append(SmoothArrow(mapping, from_point, widgets[i]))

    def _tick_arrows(self):
        offset = 0
        self.tick += 1
        for raw_i in range(len(self.arrows)):
            index = raw_i - offset
            if self.arrows[index].can_remove():
                self.arrows.pop(index)
                offset += 1
            else:
                self.arrows[index].tick()
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        for arrow in self.arrows: arrow.draw(painter, 255, 0, 0)


class SmoothArrow:
    def __init__(self, mapping, origin: QPoint, target: QWidget, smoothness=0.02, decay_speed=2, lifetime=500):
        self.aim_to(origin, target)
        self.origin_inter = QPointF(origin)
        self.target_inter = QPointF(origin)
        self.mapping      = mapping

        self.prev_targ_pos = None

        self.lifetime     = lifetime
        self.lifetime_max = lifetime
        self.decay_speed  = decay_speed

        self.smoothness  = smoothness
        self.opacity     = 0
        self.is_active   = True

    def aim_to(self, origin: QPoint, target: QWidget):
        self.origin_pos    = QPointF(origin)
        self.target_widget = target

    def refresh(self):
        self.lifetime = self.lifetime_max
        self.is_active = True

    def can_remove(self):
        return (not self.is_active) and (self.opacity == 0)

    def tick(self):
        target_pos = self.target_widget.mapTo(self.mapping, self.target_widget.pos()) + self.target_widget.rect().center()
        self.origin_inter += (self.origin_pos     - self.origin_inter) * self.smoothness
        self.target_inter += (QPointF(target_pos) - self.target_inter) * self.smoothness

        if self.prev_targ_pos != target_pos:
            self.refresh()
        self.prev_targ_pos = target_pos

        if self.is_active: self.opacity += self.decay_speed
        else:              self.opacity -= self.decay_speed
        self.opacity = max(0, min(255, self.opacity))

        self.lifetime -= 1
        if self.lifetime <= 0: self.is_active = False

    def draw(self, painter: QPainter, r:int, g: int, b: int, width=5):
        painter.setPen(QPen(QColor(r, g, b, self.opacity), width))
        draw_arrow(painter, 20, 15,
                   self.origin_inter.x(),
                   self.origin_inter.y(),
                   self.target_inter.x(),
                   self.target_inter.y())


class SingleInstanceApplication(QApplication):
    def __init__(self, *args, unique_key):
        super().__init__(*args)
        self.shared_memory = QSharedMemory(unique_key)

        if 'debug' in sys.argv[1:]: return

        if self.shared_memory.attach():
            self.alert_other_instance()
            sys.exit(0)
        else:
            # Создаем новую shared memory
            if not self.shared_memory.create(1):
                QMessageBox.critical(None, "Ошибка",
                                     "Не удалось создать уникальный маркер для приложения")
                sys.exit(1)

    def alert_other_instance(self):
        """Оповещение о существующем экземпляре"""
        QMessageBox.information(None, "Приложение уже запущено",
                                "Программа уже работает в другом окне.")


class SpoilerOptions(QPushButton):
    def __init__(self, name: str, widgets: list[QWidget] = None, collapsed=True):
        super().__init__(name)

        self.widgets = widgets if widgets else []

        self.setContentsMargins(0, 0, 0, 0)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QPushButton {
                font-size: 20px;
                font-style: italic;
                color: white;
                background-color: #111;
                border: 1px solid #333;
                padding: 10px 20px;
                border-radius: 5px;
            }

            QPushButton:hover {
                background-color: #222;
                color: #fff;
            }

            QPushButton:pressed {
                background-color: #444;
                color: #fff;
            }
        """)

        # noinspection PyUnresolvedReferences
        self.clicked.connect(self.on_click)
        self.set_hidden(collapsed)

    def set_widgets(self, widgets, parent=None):
        for w in widgets:
            if parent: w.setParent(parent)
            p = w.parent()
            if p is None:
                print("Будь добр виджеты сначала в лэйаут добавить")
                raise ValueError

        self.widgets = widgets
        self.set_shown(self.shown)

    def add_widget(self, widget):
        self.widgets.append(widget)
        self.set_shown(self.shown)

    def on_click(self):
        self.set_hidden(self.shown)

    def set_shown(self, is_shown):
        self.shown = is_shown
        if is_shown:
            for widget in self.widgets: widget.show()
        else:
            for widget in self.widgets: widget.hide()

    def set_hidden(self, is_hidden):
        self.set_shown(not is_hidden)


class ColorSelectSlider(QSlider):
    def __init__(self, min_, max_, callback):
        super().__init__(Qt.Orientation.Horizontal)

        self.setMinimumWidth(450)
        self.setMinimum(min_)
        self.setMaximum(max_)
        self.setValue(0)
        self.setTickPosition(QSlider.TickPosition.TicksBothSides)
        self.setTickInterval(30)
        self.setSingleStep(1)
        self.setPageStep(10)
        self.setInvertedAppearance(False)
        self.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #ccc;
                background: #e0e0e0;
                height: 8px;
                border-radius: 4px;
                margin: 0px 12px;
            }
            QSlider::handle:horizontal {
                background: #333;  /* Нейтральный цвет для ручки */
                border: 3px solid #111;
                height: 10px;
                width:  20px;
                margin: -5px;
                border-radius: 5px;
            }
            QSlider::sub-page:horizontal {
                background: #000; /* Цвет для заполненной части полосы */
                margin: 2px 0px 2px 15px;
                border-radius: 20px;
            }
        """)

        if callback:
            # noinspection PyUnresolvedReferences
            self.valueChanged.connect(callback)

    def wheelEvent(self, e):
        e.ignore()


class SlideButton(QPushButton):
    def __init__(self, selector, container, value, text, font, font_size, btn_size, **kwargs):
        super().__init__(str(text), **kwargs)
        self.value = value
        self.selector: DateSelector = selector
        self.container = container

        self._state = False
        self._on_click = None
        self._last_click = -1

        self.setFont(QFont(font, font_size))
        if btn_size: self.setFixedSize(btn_size, btn_size)

    # noinspection PyTypeChecker
    def updateOnMouse(self, a0):
        if self.container.isHidden(): return
        window = self.selector.parent
        # noinspection PyUnresolvedReferences
        if window.clicks == self._last_click: return
        pos = self.mapTo(window, self.rect().topLeft())

        if QRect(pos.x(), pos.y(), self.width(), self.height()).contains(a0.pos()):
            self.can_be_slided = False
            self.clicked()

    def clicked(self):
        # noinspection PyUnresolvedReferences
        self._last_click = self.selector.parent.clicks
        self._state = not self._state
        if self._on_click: self._on_click(self)

    def setState(self, state: bool):
        if self._state == state: return
        self.clicked()

    def mousePressEvent(self, e):
        super().mousePressEvent(e)
        self.clicked()

    def setOnClick(self, on_click):
        self._on_click = on_click


class CancelDate(QFrame):
    def __init__(self, app, date_text):
        super().__init__()
        self.setContentsMargins(-20, 0, -9, 0)
        layout = QHBoxLayout()

        day, month, year = map(int, date_text.split('.'))
        self.date = date(year, month, day)
        self.number = simple_button("?", "calibri", 30, 50, 'gray', bold=True,
                                    callback=lambda: app.move_up_cancel_date(self))
        self.label  = simple_label(f"{day} {months[month-1][0]} {year}", 25, italic=True)
        self.remove = icon_button("remove.svg", 50, 70, 'red',
                                  callback=lambda: app.remove_cancel_date(self))

        self.deleted = False

        layout.addWidget(self.number)
        layout.addStretch(1)
        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.remove)
        self.setLayout(layout)

    def set_number(self, i):
        self.number.setText(f'{i}')
        self.setStyleSheet(f'background-color: #{"DDD" if i % 2 else "EEE"};')

    def __eq__(self, other):
        if other.deleted: return False
        if  self.deleted: return False
        return self.label.text() == other.label.text()

    @staticmethod
    def is_valid(text: str):
        try:
            day, month, year = map(int, text.split('.'))
            date(year, month, day)
        except:
            return False
        return True


class TagSelectButton(QPushButton):
    def __init__(self, tag: Tag, other_btns):
        super().__init__(tag.name)

        self.tag = tag
        self.active = False
        self.other_btns = other_btns

        self.setFont(QFont("calibri", 20))
        set_color_scheme(self, 'gray')

        # noinspection PyUnresolvedReferences
        self.clicked.connect(self.onClick)

    def onClick(self):
        if self.active:
            self.active = False
            set_color_scheme(self, 'gray')

        else:
            for btn in self.other_btns:
                btn.active = False
                set_color_scheme(btn, 'gray')

            self.active = True
            set_color_scheme(self, self.tag.active_scheme)


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

    def mousePressEvent(self, event):
        # Проверка попадания в маркеры
        closet = min((
            ('min', self.handle_dist(event.pos(), self.min_value)),
            ('max', self.handle_dist(event.pos(), self.max_value))
        ), key=lambda x: x[1])
        if closet[1] > self.handle_radius: return

        self.active_handle      = closet[0]
        self.last_active_handle = closet[0]

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

# Ебаный костыль
class QABCMeta(type(QLineEdit), ABCMeta): pass
class CheckedLineEdit(QLineEdit, ABC, metaclass=QABCMeta):
    def __init__(self, placeholder):
        super().__init__()

        # noinspection PyTypeChecker
        self.additional_check_callable: Callable = None
        self.additional_check_error_name = "Неверное значение"

        self.setFixedHeight(40)
        self.setFont(QFont("Anonymous Pro", 20))
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.setStyleValid()
        self.textEdited.connect(self.styleChecker)

    def set_additional_check(self, additional_check, error_name=None):
        self.additional_check_callable = additional_check
        if error_name is not None:
            self.additional_check_error_name = error_name

    def setStyleValid(self):
        self.setStyleSheet("""
                    color: black;
                """)

    def setStyleInvalid(self):
        self.setStyleSheet("""
                    color: red;
                """)

    def styleChecker(self):
        try:
            value = self._parseValue()
            if self.additional_check_callable is not None:
                if not self.additional_check_callable(value):
                    raise ValueError
        except Exception:
            self.setStyleInvalid()
        else:
            self.setStyleValid()

    @abstractmethod
    def _parseValue(self): raise NotImplementedError()

    @abstractmethod
    def _unparseValue(self, *args): raise NotImplementedError()

    def getValue(self, do_additional_check=True, allow_empty=True, default=None):
        if not self.text() and allow_empty: return default
        try:
            value = self._parseValue()
            if self.additional_check_callable is not None and do_additional_check:
                if not self.additional_check_callable(value):
                    raise ValueError(self.additional_check_error_name)
            return value
        except ValueError:
            if default is not None: return default
            raise

    def setValue(self, *args, do_additional_check=True):
        if self.additional_check_callable is not None and do_additional_check:
            if not self.additional_check_callable(args[0]):
                raise ValueError(self.additional_check_error_name)
        self.setText(self._unparseValue(*args))


class PositiveIntegerSelect(CheckedLineEdit):
    def __init__(self, placeholder):
        super().__init__(placeholder)

    def _parseValue(self):
        if not self.text(): return None
        return self.parseNumber(self.text())

    def _unparseValue(self, new_value):
        return str(self.parseNumber(new_value))

    @staticmethod
    def parseNumber(number_str, allow_float=False):
        try:
            value = float(number_str)
        except ValueError:
            raise ValueError("Ожидалось число")

        if value < 0: raise ValueError("Ожидалось положительное число")

        if allow_float: return value

        if int(value) != value: raise ValueError("Ожидалось целое число")

        return int(value)


class IntegerSelect(CheckedLineEdit):
    def __init__(self, placeholder):
        super().__init__(placeholder)

    def _parseValue(self):
        if not self.text(): return None
        return self.parseNumber(self.text())

    def _unparseValue(self, new_value):
        return str(self.parseNumber(new_value))

    @staticmethod
    def parseNumber(number_str, allow_float=False):
        try:
            value = float(number_str)
        except ValueError:
            raise ValueError("Ожидалось число")

        if allow_float: return value

        if int(value) != value: raise ValueError("Ожидалось целое число")

        return int(value)


class DateSelector(QFrame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setParent(parent)
        self.parent = parent
        self.setObjectName("dateSelectorFrame")

        self.on_style  = """
            QPushButton {
                background-color: #0094D8;
                border-radius: 10px;
                border: 5px solid #0063A0;
                color: #f0f0f0;
            }
            QPushButton::hover {
                background-color: #00A4E8;
                color: #fff;
            }
            QPushButton::pressed {
                border: 5px solid #004565;
                background-color: #0063A0;
                color: #eee;
            }
        """
        self.off_style = """
            QPushButton {
                background-color: #EDEDE1;
                border-radius: 10px;
                border: 5px solid #555;
                color: #101010;
            }
            QPushButton::hover {
                background-color: #F0F0F1;
                color: #222;
            }
            QPushButton::pressed {
                border: 5px solid #000;
                background-color: #CDCDC1;
                color: #000;
            }
        """

        self.deleted = False

        self.selected_weekdays  = []
        self.selected_monthdays = []
        self.selected_months    = []
        self.selected_years     = []
        self.selected_periods   = []

        self.weekdays_btns:  list[SlideButton] = []
        self.monthdays_btns: list[SlideButton] = []
        self.months_btns:    list[SlideButton] = []
        self.years_btns:     list[SlideButton] = []
        self.periods_btns:   list[SlideButton] = []

        self.title = simple_label("Новое условие", 20, "Times New Roman")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.needed_height = 140  # Высота заголовка

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.title)
        self.layout.addSpacing(20)
        self.create_ui_switch()
        self.create_ui_weekday_select()
        self.create_ui_monthday_select()
        self.create_ui_parityday_select()
        self.create_ui_month_select()
        self.create_ui_year_select()
        self.create_ui_weekparity()
        self.create_ui_time_select()
        self.create_ui_period_select()
        self.layout.addStretch(0)

        self.short_desc_lb = simple_label("", 20)
        self.short_desc_lb.setWordWrap(True)
        self.short_desc_lb.setFixedWidth(380)
        self.short_desc_lb.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.main_contents = QWidget()
        self.main_contents.setLayout(self.layout)
        self.main_contents.setHidden(True)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.short_desc_lb)
        main_layout.addWidget(self.main_contents)
        self.setLayout(main_layout)

        self.setFixedWidth(574)

        # noinspection PyTypeChecker
        self.multi_date_type: Type = None
        self.set_to_weekday()

        self.parity = 0
        self.change_week_parity(0)

        self.delete_button    = icon_button("remove.svg", 50, 70, 'red',
                                         callback=self.remove, parent=self)

        self.clone_button     = icon_button("add.svg", 50, 70, 'blue',
                                         callback=self.clone_self, parent=self)

        self.show_hide_button = icon_button("show.svg", 50, 70, 'green',
                                        callback=self.toggle_visibility, parent=self)
        self.visibility = True
        self.toggle_visibility()

    def toggle_visibility(self):
        self.visibility = not self.visibility
        self.update_shape()

    def update_shape(self):
        if self.visibility:
            self.short_desc_lb.setVisible(False)
            self.main_contents.setVisible(True)

            self.show_hide_button.setIcon(recolor_icon("hide.svg", QColor(240, 240, 240)))

            self.setMinimumHeight(self.needed_height)
        else:
            self.short_desc_lb.setVisible(True)
            self.main_contents.setVisible(False)

            self.show_hide_button.setIcon(recolor_icon("show.svg", QColor(240, 240, 240)))

            try:
                self.short_desc_lb.setText(self.get_multidate().to_str())
            except AssertionError:
                self.short_desc_lb.setText("Неполностью заполненное условие")
            self.short_desc_lb.setFont(QFont('Calibri', 20 if len(self.short_desc_lb.text()) < 30 else 17))

            self.setMinimumHeight(70)

        # noinspection PyUnresolvedReferences
        self.parent.update_date_options()
        self.parent.update()

    def remove(self):
        self.deleted = True
        # noinspection PyUnresolvedReferences
        self.parent.update_date_options()
        # noinspection PyUnresolvedReferences
        self.parent.formula_edit.update_selectors()

        self.deleteLater()

    def set_index(self, i):
        self.title.setText(f"Условие #{i+1}")
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {"#c4c4c4" if i % 2 else "#d9d9d9"};
            }}
            #dateSelectorFrame {{
                border: 4px solid black;
            }}
        """)

    def set_current_date(self):
        if self.multi_date_type != MultiDateMonthday:
            self.set_to_monthday()

        now = datetime.now()
        for compare, btns in [
            [now.day,   self.monthdays_btns],
            [now.month, self.months_btns],
            [now.year,  self.years_btns]
        ]:
            for btn in btns: btn.setState(btn.value == compare)

    def setup_week_month_values(self, weekdays, monthdays, months, years, periods):
        for btns, compares in [
            [self.weekdays_btns,  weekdays],
            [self.monthdays_btns, monthdays],
            [self.months_btns,    months],
            [self.years_btns,     years],
            [self.periods_btns,   periods]
        ]:
            if compares is None: continue
            for btn in btns:
                btn.setState(btn.value in compares)

    def setup_parity_day_values(self, anchor: date, days_on, days_off, firstly_on):
        self.parity_anchor_selector.set_date(anchor)
        self.days_on_edit .setValue(days_on,  do_additional_check=False)
        self.days_off_edit.setValue(days_off, do_additional_check=False)
        self.change_parity_inversion(firstly_on)

    def get_parity(self):
        if self.parity == 0: return None
        return self.parity - 1

    def change_week_parity(self, new_parity=None):
        self.parity = ((self.parity + 1) if new_parity is None else new_parity) % 3

        color_norm, color_hover, color_click, color_border = color_schemes.get(['gray', 'red', 'green'][self.parity], (0, 0, 0, 0))
        self.parity_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {color_norm};
                border-radius: 10px;
                border: 5px solid {color_border};
                color: #f0f0f0;
            }}
            QPushButton::hover {{
                background-color: {color_hover};
                color: #fff;
            }}
            QPushButton::pressed {{
                border: 5px solid {color_click};
                background-color: {color_border};
                color: #eee;
            }}
        """)
        self.parity_button.setIcon(self.parity_icons[self.parity])

    def change_parity_inversion(self, new_firstly_on=None):
        self.firstly_on = not self.firstly_on if new_firstly_on is None else new_firstly_on

        set_color_scheme(self.parity_invert_btn, "red" if self.firstly_on else "green")
        self.parity_invert_btn.setIcon(recolor_icon(
            "remove.svg" if self.firstly_on else "checkmark.svg", QColor(240, 240, 240)
        ))

    def set_week_parity(self, parity):
        self.change_week_parity(0 if parity is None else parity + 1)

    def set_to_weekday(self):
        if self.multi_date_type == MultiDateWeekday: return
        self.multi_date_type = MultiDateWeekday

        self.btn_weekday.setStyleSheet(self.on_style)
        self.btn_monthday.setStyleSheet(self.off_style)
        self.btn_parityday.setStyleSheet(self.off_style)

        self.weekday_select_container.setVisible(True)
        self.monthday_select_container.setVisible(False)
        self.parityday_select_container.setVisible(False)

    def set_to_monthday(self):
        if self.multi_date_type == MultiDateMonthday: return
        self.multi_date_type = MultiDateMonthday

        self.btn_weekday.setStyleSheet(self.off_style)
        self.btn_monthday.setStyleSheet(self.on_style)
        self.btn_parityday.setStyleSheet(self.off_style)

        self.weekday_select_container.setVisible(False)
        self.monthday_select_container.setVisible(True)
        self.parityday_select_container.setVisible(False)

    def set_to_parityday(self):
        if self.multi_date_type == MultiDateParity: return
        self.multi_date_type = MultiDateParity

        self.btn_weekday.setStyleSheet(self.off_style)
        self.btn_monthday.setStyleSheet(self.off_style)
        self.btn_parityday.setStyleSheet(self.on_style)

        self.weekday_select_container.setVisible(False)
        self.monthday_select_container.setVisible(False)
        self.parityday_select_container.setVisible(True)

    def set_to_type(self, target_type):
        if   target_type == MultiDateWeekday:  self.set_to_weekday()
        elif target_type == MultiDateMonthday: self.set_to_monthday()
        elif target_type == MultiDateParity:   self.set_to_parityday()
        else:
            raise TypeError(f"Неизвестный тип условия даты: {self.multi_date_type}")

    def get_multidate(self) -> MultiDateHolder:
        time = self.time_selector.get_time_list()
        constraints = {
            "month_constraint":  self.selected_months,
            "year_constraint":   self.selected_years,
            "periods_constraint": self.selected_periods,
        }

        if self.multi_date_type == MultiDateWeekday:
            return MultiDateWeekday(time, self.selected_weekdays, **constraints)

        if self.multi_date_type == MultiDateMonthday:
            return MultiDateMonthday(time, self.selected_monthdays, **constraints)

        if self.multi_date_type == MultiDateParity:
            try:
                anchor = self.parity_anchor_selector.get_date()
                days_on = self.days_on_edit.getValue(default=0)
                assert days_on > 0, "Нужно указать кол-во дней активного периода"
                days_off = self.days_off_edit.getValue(default=0)
                assert days_off > 0, "Нужно указать кол-во дней пассивного периода"
            except ValueError as ex:
                raise AssertionError(ex.args[0])
            except InvalidSettingException:
                raise AssertionError('Нужно указать якорь для события "раз через раз"')

            return MultiDateParity(time, anchor, days_on, days_off, self.firstly_on, **constraints)


        raise TypeError(f"Неизвестный тип условия даты: {self.multi_date_type}")

    def create_ui_switch(self):
        layout = QHBoxLayout()

        self.btn_weekday = simple_button(
            "День недели", "calibri", 15, None, 0, callback=self.set_to_weekday)

        self.btn_monthday = simple_button(
            "День месяца", "calibri", 15, None, 0, callback=self.set_to_monthday)

        self.btn_parityday = simple_button(
            "Раз через раз", "calibri", 15, None, 0, callback=self.set_to_parityday)

        for btn in (self.btn_weekday, self.btn_monthday, self.btn_parityday):
            btn.setFixedSize(140, 40)

        layout.addWidget(self.btn_weekday)
        layout.addWidget(new_slash())
        layout.addWidget(self.btn_monthday)
        layout.addWidget(new_slash())
        layout.addWidget(self.btn_parityday)

        layout.addWidget(icon_button("calendar.svg", 50, 60, 'yellow',
                                     callback=self.set_current_date, icon_color=(0, 0, 0)))

        layout.addStretch(0)

        self.layout.addLayout(layout)
        self.needed_height += 60

    def create_ui_weekday_select(self):
        self.weekday_select_container = QWidget()
        self.weekday_select_container.setFixedHeight(150)
        self.needed_height += 150

        layout = QHBoxLayout()
        for i, day in enumerate(days_of_week, start=1):
            btn = SlideButton(self, self.weekday_select_container, i, day, "calibri", 25, 70)
            self.weekdays_btns.append(btn)

            def on_click(btn: SlideButton):
                if btn.value in self.selected_weekdays:
                    btn.setStyleSheet(self.off_style)
                    self.selected_weekdays.remove(btn.value)
                else:
                    btn.setStyleSheet(self.on_style)
                    self.selected_weekdays.append(btn.value)

            btn.setOnClick(on_click)
            btn.setStyleSheet(self.off_style)
            layout.addWidget(btn)
        layout.addStretch(0)

        self.weekday_select_container.setLayout(layout)
        self.layout.addWidget(self.weekday_select_container)

    def create_ui_monthday_select(self):
        self.monthday_select_container = QWidget()
        self.monthday_select_container.setFixedHeight(150)
        layout = QGridLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for i in range(0, 31):
            btn = SlideButton(self, self.monthday_select_container, i+1, i+1, "calibri", 15, 0)
            btn.setFixedSize(60, 30)
            self.monthdays_btns.append(btn)

            def on_click(btn: SlideButton):
                if btn.value in self.selected_monthdays:
                    btn.setStyleSheet(self.off_style)
                    self.selected_monthdays.remove(btn.value)
                else:
                    btn.setStyleSheet(self.on_style)
                    self.selected_monthdays.append(btn.value)

            btn.setOnClick(on_click)
            btn.setStyleSheet(self.off_style)
            width = 7
            layout.addWidget(btn, i // width, i % width)

        self.monthday_select_container.setLayout(layout)
        self.layout.addWidget(self.monthday_select_container)

    def create_ui_parityday_select(self):
        self.parityday_select_container = QWidget()
        self.parityday_select_container.setFixedHeight(150)
        # self.needed_height += 150
        layout = QGridLayout()

        # noinspection PyUnresolvedReferences
        self.parity_anchor_selector = DaySelector(self.parent.main_window, "Якорь")
        layout.addWidget(self.parity_anchor_selector, 0, 1)

        self.days_on_edit  = PositiveIntegerSelect("число")
        self.days_off_edit = PositiveIntegerSelect("число")
        self.parity_invert_btn = icon_button("", 50, 70, "gray", callback=lambda : self.change_parity_inversion())
        self.firstly_on = True
        self.change_parity_inversion(True)

        layout.addWidget(simple_label("Дней активно", 15), 1, 1)
        layout.addWidget(self.days_on_edit, 2, 1)

        layout.addWidget(simple_label("Дней пассивно", 15), 1, 2)
        layout.addWidget(self.days_off_edit, 2, 2)

        layout.addWidget(simple_label("Инвертировать?", 15), 1, 3)
        layout.addWidget(self.parity_invert_btn, 2, 3, alignment=Qt.AlignmentFlag.AlignCenter)

        self.parityday_select_container.setLayout(layout)
        self.layout.addWidget(self.parityday_select_container)

    def create_ui_month_select(self):
        self.month_select_container = QWidget()
        self.month_select_container.setFixedHeight(110)
        self.needed_height += 110

        layout = QGridLayout()
        for i, day in enumerate(months):
            btn = SlideButton(self, self.month_select_container, i+1, f'{day[3]}, {i+1}', "calibri", 17, None)
            btn.setFixedSize(83, 45)
            self.months_btns.append(btn)

            def on_click(btn: SlideButton):
                if btn.value in self.selected_months:
                    btn.setStyleSheet(self.off_style)
                    self.selected_months.remove(btn.value)
                else:
                    btn.setStyleSheet(self.on_style)
                    self.selected_months.append(btn.value)

            btn.setOnClick(on_click)
            btn.setStyleSheet(self.off_style)
            layout.addWidget(btn, i // 6, i % 6)

        self.month_select_container.setLayout(layout)
        self.layout.addWidget(self.month_select_container)

    def create_ui_year_select(self):
        self.year_select_container = QWidget()
        self.year_select_container.setFixedHeight(50)
        self.needed_height += 50

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        year = datetime.now().year
        for i in range(year - 1, year + 4 + 1):
            btn = SlideButton(self, self.year_select_container, i, f'{i}', "calibri", 20, None)
            btn.setFixedSize(83, 45)
            self.years_btns.append(btn)

            def on_click(btn: SlideButton):
                if btn.value in self.selected_years:
                    btn.setStyleSheet(self.off_style)
                    self.selected_years.remove(btn.value)
                else:
                    btn.setStyleSheet(self.on_style)
                    self.selected_years.append(btn.value)

            btn.setOnClick(on_click)
            btn.setStyleSheet(self.off_style)
            layout.addWidget(btn)

        self.year_select_container.setLayout(layout)
        self.layout.addWidget(new_separator(h=3))
        self.layout.addWidget(self.year_select_container)

    def create_ui_weekparity(self):
        layout = QHBoxLayout()

        self.parity_icons = [
            recolor_icon("dont_care.svg", QColor(240, 240, 240)),
            recolor_icon("remove.svg",    QColor(240, 240, 240)),
            recolor_icon("checkmark.svg", QColor(240, 240, 240))
        ]
        self.parity_button = QPushButton()
        self.parity_button.setFixedSize(50, 50)
        self.parity_button.setIconSize(QSize(70, 70))
        # noinspection PyUnresolvedReferences
        self.parity_button.clicked.connect(lambda : self.change_week_parity())

        lb = simple_label("Чётность недели - ", 30)
        layout.addWidget(lb)
        layout.addWidget(self.parity_button)
        layout.addStretch(0)

        self.layout.addLayout(layout)
        self.needed_height += self.parity_button.height()

    def create_ui_time_select(self):
        self.time_selector = TimeSelector(8, 24)
        self.needed_height += self.time_selector.height()
        self.layout.addWidget(self.time_selector)

    def create_ui_period_select(self):
        max_row = max((i.row for i in all_periods.values()))

        self.period_select_container = QWidget()
        self.period_select_container.setFixedHeight(50 * max_row)
        self.needed_height += 50 * max_row

        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        rows = {}
        for name, period in all_periods.items():
            btn = SlideButton(self, self.period_select_container, name, f" {name} ", "calibri", 20, None)
            btn.setFixedHeight(45)
            self.periods_btns.append(btn)

            def on_click(btn: SlideButton):
                if btn.value in self.selected_periods:
                    btn.setStyleSheet(self.off_style)
                    self.selected_periods.remove(btn.value)
                else:
                    btn.setStyleSheet(self.on_style)
                    self.selected_periods.append(btn.value)

            btn.setOnClick(on_click)
            btn.setStyleSheet(self.off_style)

            rows[period.row] = rows.get(period.row, 0) + 1
            layout.addWidget(btn, period.row, rows[period.row])

        self.period_select_container.setLayout(layout)
        self.layout.addWidget(new_separator(h=3))
        self.layout.addWidget(self.period_select_container)

    def clone_self(self):
        clone = DateSelector(self.parent)
        clone.setup_week_month_values(self.selected_weekdays, self.selected_monthdays, self.selected_months,
                                      self.selected_years, self.selected_periods)

        clone.parity_anchor_selector.line_edit.setText(
            self.parity_anchor_selector.line_edit.text()
        )
        clone.days_on_edit.setText(self.days_on_edit.text())
        clone.days_off_edit.setText(self.days_off_edit.text())
        clone.firstly_on = self.firstly_on

        clone.change_week_parity(self.parity)

        clone.time_selector.set_min(self.time_selector.min_value)
        clone.time_selector.set_max(self.time_selector.max_value)

        if self.multi_date_type == MultiDateWeekday:
            clone.set_to_monthday()
        if self.multi_date_type == MultiDateMonthday:
            clone.set_to_monthday()
        if self.multi_date_type == MultiDateParity:
            clone.set_to_parityday()

        # noinspection PyUnresolvedReferences
        self.parent.add_date_option(clone)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        start_pos      = 11
        between_offset = 10

        for btn in [self.delete_button, self.clone_button, self.show_hide_button]:
            btn.move(self.width() - start_pos - btn.width(), 10)
            start_pos += btn.width() + between_offset


class BubbleWidget(QWidget):
    def __init__(self, text, width=200, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.label = QLabel(text)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 240);
                color: white;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
        """)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(width)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self.opacity_effect)

        self._fade_in_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self._fade_in_animation.setDuration(200)
        self._fade_in_animation.setStartValue(0.0)
        self._fade_in_animation.setEndValue(1.0)
        self._fade_in_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

        self._fade_out_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self._fade_out_animation.setDuration(200)
        self._fade_out_animation.setStartValue(1.0)
        self._fade_out_animation.setEndValue(0.0)
        self._fade_out_animation.finished.connect(self.hide)
        self._fade_out_animation.setEasingCurve(QEasingCurve.Type.OutQuad)

    def showEvent(self, event):
        self._fade_out_animation.stop()

        self._fade_in_animation.stop()
        self._fade_in_animation.start()
        super().showEvent(event)

    def fadeOutAnimation(self):
        self._fade_in_animation.stop()

        self._fade_out_animation.stop()
        self._fade_out_animation.start()


class WhatsThisMarker(QPushButton):
    def __init__(self, hint: str, direction: Qt.AlignmentFlag = None, width=200):
        super().__init__()
        self.hint = hint

        self.direction = Qt.AlignmentFlag.AlignTop if direction is None else direction

        self.setIcon(QIcon("icons/whats_this.png"))
        self.setFixedSize(30, 30)
        self.setIconSize(QSize(30, 30))
        self.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
        """)

        self.bubble = BubbleWidget(hint, width=width)
        self.bubble.hide()

        self.setMouseTracking(True)

    def enterEvent(self, event: QEnterEvent):
        if not self.bubble.isVisible():
            self.update_bubble_position()
            self.bubble.show()
            self.bubble.raise_()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.bubble.fadeOutAnimation()
        super().leaveEvent(event)

    def hideEvent(self, event):
        self.bubble.hide()
        super().hideEvent(event)

    def update_bubble_position(self):
        """Обновляет позицию плашки и стрелки"""
        button_global_pos = self.mapToGlobal(QPoint(0, 0))

        # Рассчитываем позицию плашки над кнопкой
        bubble_height = self.bubble.sizeHint().height()
        bubble_width = self.bubble.sizeHint().width()

        # Центрируем плашку над кнопкой
        x_left   = button_global_pos.x() - bubble_width
        x_center = button_global_pos.x() + (self.width() - bubble_width) // 2
        x_right  = button_global_pos.x() + self.width()

        y_top    = button_global_pos.y() - bubble_height
        y_center = button_global_pos.y() + (self.height() - bubble_height) // 2
        y_bottom = button_global_pos.y() + self.height()

        if self.direction == Qt.AlignmentFlag.AlignTop:
            self.bubble.move(int(x_center), int(y_top))
        elif self.direction == Qt.AlignmentFlag.AlignBottom:
            self.bubble.move(int(x_center), int(y_bottom))
        elif self.direction == Qt.AlignmentFlag.AlignRight:
            self.bubble.move(int(x_right), int(y_center))
        elif self.direction == Qt.AlignmentFlag.AlignLeft:
            self.bubble.move(int(x_left), int(y_center))
        else:
            raise TypeError(f"Неизвестный тип выравнивания плашки {self.direction}")

    def resizeEvent(self, event):
        if self.bubble.isVisible():
            self.update_bubble_position()
        super().resizeEvent(event)

    def moveEvent(self, event):
        if self.bubble.isVisible():
            self.update_bubble_position()
        super().moveEvent(event)


class TimePeriodSelector(QFrame):
    def __init__(self, main_window, remove_function):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.name_edit = simple_line_input("Название периода", 16)
        layout.addWidget(self.name_edit, 4)

        self.st_selector = DaySelector(main_window, "Начало")
        self.en_selector = DaySelector(main_window, "Начало")

        layout.addWidget(self.st_selector)
        layout.addWidget(simple_label("-", 20))
        layout.addWidget(self.en_selector)

        self.btn_row_remove = icon_button("left.svg", 50, 70,  'gray',
                                               callback=lambda: self.update_row(self.row - 1))
        self.btn_row_add    = icon_button("right.svg", 50, 70, 'green',
                                               callback=lambda: self.update_row(self.row + 1))
        self.update_row(1)

        delete_btn = icon_button(
            "remove.svg", 30, 30, 'red',
            callback=lambda : remove_function(self)
        )
        layout.addWidget(delete_btn)

    def update_row(self, new_row):
        self.row = max(1, new_row)
        set_color_scheme(self.btn_row_remove, 'red' if self.row > 1 else 'gray')

    def get_time_period(self):
        if not self.name_edit.text(): raise InvalidSettingException("Укажи имя!", self.name_edit)
        dates = [date(e.year, e.month, e.day) for e in (self.st_selector.get_date(), self.en_selector.get_date())]
        if dates[0] > dates[1]:
            raise InvalidSettingException("Дата конца раньше даты начала!", self.st_selector, self.en_selector)
        return TimePeriod(*dates)


class DaySelector(QFrame):
    def __init__(self, main_window, placeholder="DD.MM.YYYY", font_size=15):
        super().__init__()
        font = QFont("calibri", font_size)

        self.setFixedSize(170, 50)
        self.setContentsMargins(0, 0, 0, 0)

        self.layout = QHBoxLayout()

        self.line_edit = QLineEdit()
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setFont(font)
        self.line_edit.setPlaceholderText(placeholder)
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.edit_btn = icon_button("pick.svg", 30, 37, 'yellow',
                                    icon_color=(0, 0, 0), callback=self.toggle_popup)

        self.layout.addWidget(self.line_edit)
        self.layout.addWidget(self.edit_btn)
        self.setLayout(self.layout)

        self.popup = CalendarPopup(self, self.line_edit, main_window=main_window)
        self.popup.hide()

    def get_date(self):
        try:
            day, month, year = map(int, self.line_edit.text().split('.'))
            return date(year, month, day)
        except:
            raise InvalidSettingException("Неверная дата!", self.line_edit)

    def set_date(self, new_date: date):
        self.line_edit.setText(datetime_to_str(new_date))

    def toggle_popup(self):
        self.popup.update_position(self.edit_btn)
        self.popup.update_view()
        self.popup.show()


class CalendarPopup(QFrame):
    def __init__(self, parent, obj_to_edit: QWidget | Callable, pick_date: datetime | date = None,
                 main_window=None, custom_style_callback: Callable[[date, "SegmentedButton"], None]=None):
        super().__init__(parent)
        if pick_date is None: pick_date = datetime.today()
        self.pick_date = date(pick_date.year, pick_date.month, 1)
        self.original_pick_date = pick_date.date() if isinstance(pick_date, datetime) else pick_date

        assert is_main_window(main_window), 'Должен быть класс главного окна'
        self.main_window = main_window

        self.obj_to_edit = obj_to_edit
        self.custom_style_callback = custom_style_callback

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
        self.setFixedSize(250, 270)

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

            # if day != day:
            #     btn.draw_circle_offset = -1
            #     btn.setStyleSheet(
            #         # background: rgba(0, 120, 212, 0.8);
            #         """
            #             SegmentedButton {
            #                 border: 3px solid #7800d4;
            #                 border-radius: 5px;
            #                 background: transparent;
            #                 color: black;
            #                 font-weight: bold;
            #             }
            #             SegmentedButton:hover {
            #                 border: 5px solid #0078d4;
            #             }
            #         """
            #     )

            # noinspection PyUnresolvedReferences
            btn.clicked.connect(lambda _, d=day: self.on_date_selected(d))

            self.grid_layout.addWidget(btn, *divmod(index + 7, 7))
            self.day_buttons.append(btn)
            # noinspection PyTypeChecker
            btns.append(defaultdict(list, [("btn", btn)]))

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


class AnnouncedTaskSelect(QComboBox):
    def __init__(self):
        super().__init__()

        self.elements = {}

        self.setStyleSheet("""
            QWidget {
                border: 3px solid #333;
                padding-left: 10px;
                border-radius: 5px;
                font-size: 25px;
            }
            
            QComboBox::drop-down {
                border: none;
                width: 50px;
                height: 50px;
                subcontrol-origin: padding;
                subcontrol-position: center right;
            }
            
            QComboBox::down-arrow {
                width: 50px;
                height: 50px;
                image: url(icons/down.svg);
            }
        """)
        self.setMaximumWidth(500)
        self.setFixedHeight(50)

        self.updater_timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.updater_timer.timeout.connect(self.update_tasks)
        self.updater_timer.start(1000)
        self.update_tasks()

    def update_tasks(self):
        tasks = [file for file in os.listdir("announced_tasks") if file.endswith(".json")]
        if tasks == list(self.elements.keys()): return

        self.clear()
        self.elements.clear()

        model = QStandardItemModel()

        option = None
        for file in tasks:
            try:
                with open(f'announced_tasks/{file}', 'r', encoding="UTF-8") as f:
                    task = AnnouncedTask.from_json(file, json.load(f))

                    option = QStandardItem(task.display_name)
                    option.setData(task, Qt.ItemDataRole.UserRole)

                    self.elements[file] = task
            except Exception as ex:
                option = QStandardItem(f"{file} // {ex}")
                option.setForeground(QColor(255, 0, 0))
            finally:
                model.appendRow(option)

        self.setModel(model)

    def currentTask(self):
        return self.currentData(Qt.ItemDataRole.UserRole)

    def wheelEvent(self, e):
        e.ignore()


class AnnouncedTaskSetup(QFrame):
    def __init__(self, task: AnnouncedTask):
        super().__init__()

        self.task = task

        self.setObjectName("mainFrame")
        self.setStyleSheet("""
            #mainFrame {
                border: 3px solid #333;
                border-radius: 5px;
                font-size: 25px;
            }
        """)

        self.task_title = simple_label(f'"{task.display_name}"', 20)
        self.task_title.setWordWrap(True)
        self.before_type_combo = simple_combo_box([
            "за N минут", "N мин. / после", "Если просрочено"], 16)
        self.before_minutes_input = simple_line_input("N", 16)
        self.remove_button = simple_button("Удалить", "calibri", 16, 40,
                                           callback=self.deleteLater)

        if task.delay >= 0:
            hour, mins = divmod(task.delay, 60)
            self.before_minutes_input.setText(f'{hour}:{"0" if mins < 10 else ""}{mins}'
                                              if hour > 0 else str(task.delay))

            if not task.do_expire:
                self.before_type_combo.setCurrentIndex(0) # за N минут
            else:
                self.before_type_combo.setCurrentIndex(1) # N мин. / после
        else:
            self.before_type_combo.setCurrentIndex(2) # Если просрочено

        set_color_scheme(self.remove_button, 'red')

        layout = QHBoxLayout()

        setup_layout = QVBoxLayout()
        setup_layout.addWidget(self.task_title)
        setup_layout.addWidget(self.before_type_combo)
        setup_layout.addWidget(self.before_minutes_input)
        setup_layout.addWidget(self.remove_button)
        for i in range(setup_layout.count()): setup_layout.itemAt(i).widget().setFixedWidth(200)

        if not task.params_scheme:
            self.task_title.setFixedWidth(550)

        layout.addLayout(setup_layout)

        # =====

        self.params_layout = QVBoxLayout()
        layout.addLayout(self.params_layout)
        for k, v in task.params_scheme.items():
            self.params_layout.addWidget(AnnouncedParameter(k, v, task.params.get(k)))

        self.setLayout(layout)

    def build_task(self):
        for i in range(self.params_layout.count()):
            w = self.params_layout.itemAt(i).widget()
            if not isinstance(w, AnnouncedParameter): continue
            if not w.input.text(): continue

            self.task.params[w.name] = w.input.text()

        on_expire   = self.before_type_combo.currentIndex() >= 1
        ensure_time = self.before_type_combo.currentIndex() <= 1

        minutes = -1
        text = self.before_minutes_input.text()
        try:
            if ensure_time:
                if ":" in text:
                    hour, mins = map(int, text.split(":"))
                    minutes = hour * 60 + mins
                else:
                    minutes = int(text)
        except ValueError:
            raise AssertionError('Укажи кол-во минут перед задачей')
        except:
            raise AssertionError(f'Не верный формат времени перед задачей - "{text}", hh:mm')

        self.task.delay     = minutes
        self.task.do_expire = on_expire

        return self.task


class AnnouncedParameter(QFrame):
    def __init__(self, name, _type, value=None):
        super().__init__()
        self.name = name
        self.type = _type

        self.input = simple_line_input(_type, 16)
        if value: self.input.setText(value)

        layout = QHBoxLayout()
        layout.addWidget(simple_label(name.capitalize() + ":", 22))
        layout.addWidget(self.input)

        v = abs(hash(name + _type)) % (55 ** 3)
        rg, b = divmod(v, 55)
        r, g = divmod(rg, 55)
        set_custom_color_scheme(self, *[a + 100 for a in (r, g, b)], element_name="#paramFrame",
                                after="QWidget { background-color: transparent; color: white; }")

        self.setObjectName("paramFrame")
        self.setFixedHeight(60)
        self.setLayout(layout)


class EventSelector(QFrame):
    def __init__(self, parent):
        super().__init__(parent)
        self.app = parent

        self.setHidden(True)
        self.setObjectName("mainFrame")
        self.setStyleSheet("""
        #mainFrame {
            background-color: #EDEDE1;
            border-radius: 10px;
            border: 5px solid #555;
            color: #000;
        }
        """)

        events_content = QWidget()
        events_content.setMinimumWidth(0)

        self.events_layout = QVBoxLayout(events_content)
        self.events_layout.setContentsMargins(0, 0, 0, 0)

        self.events_scroll = QScrollArea()
        self.events_scroll.setWidgetResizable(True)
        self.events_scroll.setWidget(events_content)
        self.events_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.events_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.events_scroll.setStyleSheet('background-color: transparent;')
        self.events_scroll.setFixedHeight(420)

        self.main_layout = QVBoxLayout()
        self.main_layout.addWidget(self.events_scroll)
        self.main_layout.addWidget(icon_button(
            "remove.svg", 50, 70, 'red',
            callback=lambda: self.setHidden(True)
        ))
        self.main_layout.addStretch(1)

        self.setLayout(self.main_layout)
        self.setFixedSize(300, 500)

    def set_events(self, events: list[ScheduleEvent]):
        for i in range(self.events_layout.count()):
            w = self.events_layout.itemAt(i).widget()
            if w is None: continue
            w.deleteLater()

        # noinspection PyUnresolvedReferences
        def on_click_edit(button: EventButton):
            self.app.create_task_add_form(button.event)
            self.setHidden(True)

        all_sorted = sorted(((e, e.get_next_timestamp(datetime.now().date())) for e in events),
                            key=lambda x: x[0].get_sort_value() if x[1] is None else x[1].get_start_datetime().timestamp())

        for i, (name, is_hidden, is_expired) in enumerate([
            ["Основные", False, False],
            ["Истёкшие", False, True ],
            ["Скрытые",  True,  None ]
        ]):
            widgets = []
            for event, date in all_sorted:
                if is_hidden  is not None  and  is_hidden  ^ (Tags.HIDDEN.YES in event.tags): continue
                if is_expired is not None  and  is_expired ^ (date is None): continue

                btn = EventButton(event, callback=on_click_edit)
                widgets.append(btn)

            if not widgets: continue

            spoiler = SpoilerOptions(name, collapsed= i != 0)
            self.events_layout.addWidget(spoiler)

            for widget in widgets: self.events_layout.addWidget(widget)

            spoiler.set_widgets(widgets)
            self.events_layout.addWidget(new_separator(h=3))

        self.events_layout.addStretch(0)

        self.events_scroll.verticalScrollBar().setValue(0)
        self.setVisible(True)


class UpcomingEvents(QFrame):
    def __init__(self, parent, is_hidden=False):
        super().__init__(parent)
        self.app = parent

        self.collapsed = False
        self.setObjectName("mainFrame")
        self.setStyleSheet("""
        #mainFrame {
            background-color: #EDEDE1;
            border-radius: 10px;
            border: 5px solid #555;
            color: #000;
        }
        """)

        events_content = QWidget()
        events_content.setMinimumHeight(0)

        events_content = QWidget()
        events_content.setMinimumWidth(0)

        self.events_layout = QVBoxLayout(events_content)
        self.events_layout.setContentsMargins(0, 0, 0, 0)

        self.events_scroll = QScrollArea()
        self.events_scroll.setWidgetResizable(True)
        self.events_scroll.setWidget(events_content)
        self.events_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.events_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.events_scroll.setStyleSheet('background-color: transparent;')

        self.events:         list[ScheduleEvent] = []
        self.events_buttons: list[EventButton]   = []

        self.hidden = not is_hidden
        self.hide_btn = QPushButton()
        self.hide_btn.setFixedSize(8, 90)
        set_color_scheme(self.hide_btn, 'gray')
        # noinspection PyUnresolvedReferences
        self.hide_btn.clicked.connect(self.toggle_visibility)

        self.toggle_btn = icon_button(
            "up.svg", 0, 90, 'blue',
            callback=self.toggle_view
        )
        self.toggle_btn.setFixedSize(50, 70)

        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(0, 0, 10, 0)

        self.sub_layout = QHBoxLayout()
        self.sub_layout.addWidget(self.hide_btn)
        self.sub_layout.addWidget(self.toggle_btn)
        self.remove_from = 2

        self.main_layout.addLayout(self.sub_layout)
        self.main_layout.addWidget(self.events_scroll)
        self.main_layout.addStretch(0)

        self.setLayout(self.main_layout)

        self.timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.update_timers)
        self.timer.start(1000)

        self.toggle_view()
        self.toggle_visibility()

    def toggle_visibility(self):
        self.hidden = not self.hidden
        if self.hidden and not self.collapsed: self.toggle_view()

        self.setFixedWidth(30 if self.hidden else 300)
        self.hide_btn.setFixedWidth(20 if self.hidden else 8)
        for i in range(1, self.sub_layout.count()):
            w = self.sub_layout.itemAt(i).widget()
            w.setHidden(self.hidden)

        if self.app.loaded:
            self.app.cfg.save(upcoming_hidden=self.hidden)
            self.app.resizeEvent(None)

    def toggle_view(self):
        self.collapsed = not self.collapsed
        if self.collapsed:
            self.setFixedHeight(100)
            self.events_scroll.setHidden(True)
            self.toggle_btn.setIcon(recolor_icon("down.svg", QColor(240, 240, 240)))
        else:
            self.setFixedHeight(300)
            self.events_scroll.setVisible(True)
            self.toggle_btn.setIcon(recolor_icon("up.svg", QColor(240, 240, 240)))

    def update_events(self, events: list[ScheduleEvent]):
        self.events.clear()
        self.events_buttons.clear()

        for i in range(self.remove_from, self.sub_layout.count()):
            w = self.sub_layout.itemAt(i).widget()
            w.deleteLater()

        for i in range(self.events_layout.count()):
            w = self.events_layout.itemAt(i).widget()
            w.deleteLater()

        # noinspection PyUnresolvedReferences
        now: datetime = self.app.get_now()
        def tracking(event: ScheduleEvent):
            if event.tags.have(Tags.TRACKING.NO): return False
            if (Tags.TRACKING not in event.tags) and (not event.tags.have(Tags.IMPORTANT.YES)): return False

            next_stamp = event.get_next_timestamp(now.date())
            if next_stamp is None: return False
            start_date, end_date = next_stamp.as_datetimes()
            if now > end_date: return False

            if event.tags.have(Tags.IMPORTANT.YES): return True

            if start_date - now > timedelta(days=31): return False

            if event.tags.have(Tags.TRACKING.YES):  return True

            return False

        # TODO: почему-то если поставить огромную конечную дату, то оно дико виснет
        # TODO: и ещё если убрать все события без ограничения по времени то код супер быстро отрабатывает
        # events = [event for event in events if event.times != 0]

        with DebugTimer("Вычисление дат (+месяц)"):
            st = time()
            next_dates2 = {
                event: next(event.get_final_timestamps(now.date(), now.date() + timedelta(days=31)), None)
                for event in events
            }
            print("2", time() - st)

        # with DebugTimer("Вычисление дат (9999 год)"):
        #     st = time()
        #     next_dates = {
        #         event: next(event.get_final_timestamps(now.date(), date(9998, 1, 1)), None)
        #         for event in events
        #     }
        #     print("1", time() - st)
        return

        # event.get_next_timestamp(now.date()).get_start_datetime()
        sorted_events = sorted(
            ((event, None) for event in events if tracking(event)),
            key=lambda x: x[1])

        if not sorted_events:
            return self.setHidden(True)
        self.setVisible(True)

        prev_date = None
        for i, (event, start_date) in enumerate(sorted_events):
            if start_date is None: continue
            btn = EventButton(event, second_label=True)
            btn.set_on_click_editor(self.app)

            self.events.append(event)
            self.events_buttons.append(btn)
            if i == 0:
                btn.setFixedHeight(70)
                if self.hidden: btn.setHidden(True)
                self.sub_layout.addWidget(btn)
            else:
                if prev_date != start_date.date() and prev_date is not None:
                    self.events_layout.addWidget(new_separator(h=4))
                self.events_layout.addWidget(btn)
                prev_date = start_date.date()

        self.update_timers()

    def update_timers(self):
        if not self.events: return

        # noinspection PyUnresolvedReferences
        now = self.app.get_now()

        more_events = 0
        first_day = None
        for i, (event, button) in enumerate(zip(self.events, self.events_buttons)):
            event: ScheduleEvent
            button: EventButton

            start_date, end_date = event.get_next_timestamp(now).as_datetimes()
            if start_date is None or now > end_date: return self.update_events(self.events.copy())

            minutes = ceil((start_date - now).total_seconds() / 60)

            prefix = "" if i == 0 else "Остаётся: "
            subtitle = f'{prefix}{beauty_time(minutes)}' if minutes > 0 else "Сейчас"

            button.lb_subtitle.setText(subtitle)

            if i == 0: first_day = start_date
            else:
                if start_date.date() == first_day.date():
                    more_events += 1

        if more_events > 0:
            minutes = ceil((first_day - now).total_seconds() / 60)
            self.events_buttons[0].lb_subtitle.setText(
                f'{beauty_time(minutes) if minutes > 0 else "Сейчас"} (+{more_events})'
            )


class EventButton(QPushButton):
    def __init__(self, event: ScheduleEvent, override_important=None, second_label=False, callback=None):
        super().__init__()

        self.lb_title = QLabel(f'<div style="line-height: 0.9;">{event.name}</div>')
        self.lb_subtitle = QLabel("Subtitle")

        for label, font_size in ((self.lb_title, 20), (self.lb_subtitle, 14)):
            label.setFont(QFont("calibri", font_size))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("background-color: transparent;")

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 5)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(self.lb_title)
        if second_label:
            layout.addWidget(self.lb_subtitle)

        self.event = event
        self.important = override_important or event.tags.have(Tags.IMPORTANT.YES)


        set_custom_color_scheme(self, *event.color,
                                addition="border: 8px solid rgb(30, 30, 30);" if self.important else "")

        self.setFixedHeight(70 if self.important else 60)
        self.click_event = None

        # noinspection PyUnresolvedReferences
        self.clicked.connect(self.on_click)

        self.setLayout(layout)

        if self.important:
            self.frame = 0
            self.timer = QTimer(self)
            # noinspection PyUnresolvedReferences
            self.timer.timeout.connect(self.next_frame)
            self.timer.start(1000 // 60)

        if callback:
            self.set_on_click(callback)

    def paintEvent(self, a0):
        super().paintEvent(a0)

        if not self.important: return

        paint_highlighted_border(self, self.frame, QColor(255, 0, 0), 150, True, 4)

    def set_on_click(self, on_click_func):
        self.click_event = on_click_func

    def set_on_click_editor(self, app):
        self.click_event = lambda _: app.create_task_add_form(self.event)

    def on_click(self):
        if self.click_event: self.click_event(self)

    def next_frame(self):
        self.frame += 1
        self.update()