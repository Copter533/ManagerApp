import json
import json
import math
import os
import sys
from datetime import datetime, date, timedelta
from math import atan2, sin, cos, radians, ceil
from typing import Type

from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QTimer, QSharedMemory, QRectF, QPointF
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QFontDatabase, QAction, QStandardItem, \
    QStandardItemModel
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QFrame, QGridLayout, QGraphicsDropShadowEffect, QSlider,
    QLineEdit, QVBoxLayout, QScrollArea, QTextEdit, QApplication, QComboBox, QMessageBox, QStyleOptionButton, QStyle,
    QLayout, QBoxLayout
)

from announced_task import AnnouncedTask
from tags import Tags, Tag
from utils import days_of_week, months, ScheduleEvent, rgb_to_hex, str_time, interpolate, beauty_time, all_periods, \
    MultiDate, beauty_date, TimePeriod, is_main_window

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

        for i, (layout_type, ui_creator) in enumerate(category_options):
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
        if self.shared_memory.attach():
            self.alert_other_instance()
            if not 'debug' in sys.argv[1:]:
                sys.exit(0)
        else:
            if not self.shared_memory.create(1):
                QMessageBox.critical(None, "Ошибка", "Не удалось создать уникальный маркер для приложения")
                sys.exit(1)

    def alert_other_instance(self):
        print("Multiple runs")


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
                border-radius: 5px; /* добавим немного округления углов */
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
        painter.drawPolygon([QPoint(x, y+dx), QPoint(x+dx, y+dx*2), QPoint(x-dx, y+dx*2)])

        painter.setPen(QPen(QColor.fromHsv(color.hue(), color.saturation(), color.value()+40), dx))
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

        self.is_weekday = False
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

            d = MultiDate()
            self.add_multidate_state(d)
            self.short_desc_lb.setText(str(d))
            self.short_desc_lb.setFont(QFont('Calibri', 20 if len(self.short_desc_lb.text()) < 30 else 17))

            self.setMinimumHeight(70)

        # noinspection PyUnresolvedReferences
        self.parent.update_date_options()
        self.parent.update()

    def remove(self):
        self.deleted = True
        # noinspection PyUnresolvedReferences
        self.parent.update_date_options()

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
        if self.is_weekday: self.set_to_monthday()

        now = datetime.now()
        for compare, btns in [
            [now.day,   self.monthdays_btns],
            [now.month, self.months_btns],
            [now.year,  self.years_btns]
        ]:
            for btn in btns: btn.setState(btn.value == compare)

    def setup_values(self, weekdays, monthdays, months, years, periods):
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

    def set_parity(self, parity):
        self.change_week_parity(0 if parity is None else parity + 1)

    def set_to_weekday(self):
        if self.is_weekday: return
        self.is_weekday = True

        self.btn_weekday.setStyleSheet(self.on_style)
        self.btn_monthday.setStyleSheet(self.off_style)
        self.btn_parityday.setStyleSheet(self.off_style)

        self.weekday_select_container.setVisible(True)
        self.monthday_select_container.setVisible(False)
        self.parityday_select_container.setVisible(False)

    def set_to_monthday(self):
        if not self.is_weekday: return
        self.is_weekday = False

        self.btn_weekday.setStyleSheet(self.off_style)
        self.btn_monthday.setStyleSheet(self.on_style)
        self.btn_parityday.setStyleSheet(self.off_style)

        self.weekday_select_container.setVisible(False)
        self.monthday_select_container.setVisible(True)
        self.parityday_select_container.setVisible(False)

    def set_to_parityday(self):
        # if not self.is_weekday: return
        # self.is_weekday = False

        self.btn_weekday.setStyleSheet(self.off_style)
        self.btn_monthday.setStyleSheet(self.off_style)
        self.btn_parityday.setStyleSheet(self.on_style)

        self.weekday_select_container.setVisible(False)
        self.monthday_select_container.setVisible(False)
        self.parityday_select_container.setVisible(True)

    def add_multidate_state(self, date: MultiDate):
        date.add_state(
            weekday  = self.selected_weekdays  if     self.is_weekday else None,
            monthday = self.selected_monthdays if not self.is_weekday else None,
            month    = self.selected_months,
            year     = self.selected_years,
            parity   = self.get_parity(),
            time     = self.time_selector.get_timedur(),
            periods  = self.selected_periods
        )

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
        # self.needed_height += 150
        layout = QGridLayout()

        for i in range(0, 31):
            btn = SlideButton(self, self.monthday_select_container, i+1, i+1, "calibri", 15, 40)
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
            layout.addWidget(btn, i // 11, i % 11)

        self.monthday_select_container.setLayout(layout)
        self.layout.addWidget(self.monthday_select_container)

    def create_ui_parityday_select(self):
        self.parityday_select_container = QWidget()
        self.parityday_select_container.setFixedHeight(150)
        # self.needed_height += 150
        layout = QGridLayout()

        # noinspection PyUnresolvedReferences
        layout.addWidget(DaySelector(self.parent.main_window, "Якорь"), 1, 2)

        layout.addWidget(simple_label("You", 20), 1, 1)
        layout.addWidget(simple_label("been", 20), 2, 2)
        layout.addWidget(simple_label("trolled", 20), 3, 3)
        # for i in range(0, 31):
        #     btn = SlideButton(self, self.monthday_select_container, i+1, i+1, "calibri", 15, 40)
        #     self.monthdays_btns.append(btn)
        #
        #     def on_click(btn: SlideButton):
        #         if btn.value in self.selected_monthdays:
        #             btn.setStyleSheet(self.off_style)
        #             self.selected_monthdays.remove(btn.value)
        #         else:
        #             btn.setStyleSheet(self.on_style)
        #             self.selected_monthdays.append(btn.value)
        #
        #     btn.setOnClick(on_click)
        #     btn.setStyleSheet(self.off_style)
        #     layout.addWidget(btn, i // 11, i % 11)

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
        clone.setup_values(self.selected_weekdays, self.selected_monthdays, self.selected_months,
                           self.selected_years, self.selected_periods)
        clone.change_week_parity(self.parity)

        clone.time_selector.set_min(self.time_selector.min_value)
        clone.time_selector.set_max(self.time_selector.max_value)

        if not self.is_weekday: clone.set_to_monthday()

        # noinspection PyUnresolvedReferences
        self.parent.add_date_option(clone)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        start_pos      = 11
        between_offset = 10

        for btn in [self.delete_button, self.clone_button, self.show_hide_button]:
            btn.move(self.width() - start_pos - btn.width(), 10)
            start_pos += btn.width() + between_offset


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

    def toggle_popup(self):
        self.update_popup_position()
        self.popup.update_view()
        self.popup.show()

    def update_popup_position(self):
        btn_global_pos = self.edit_btn.mapToGlobal(QPoint(0, self.edit_btn.height()))
        screen_geo = self.screen().availableGeometry()

        popup_width = self.popup.width()
        popup_height = self.popup.height()

        # Рассчитываем позицию по X
        x = btn_global_pos.x()
        if x + popup_width > screen_geo.right():
            x = screen_geo.right() - popup_width
        x = max(x, screen_geo.left())

        # Рассчитываем позицию по Y
        y = btn_global_pos.y()
        if y + popup_height > screen_geo.bottom():
            y = btn_global_pos.y() - popup_height - self.edit_btn.height()
        y = max(y, screen_geo.top())

        self.popup.move(int(x), int(y))


class CalendarPopup(QFrame):
    def __init__(self, parent, obj_to_edit: QWidget, pick_date: [datetime | date] = None, main_window=None):
        super().__init__(parent)
        if pick_date is None: pick_date = datetime.today()
        self.pick_date = date(pick_date.year, pick_date.month, 1)

        assert is_main_window(main_window), 'Должен быть класс главного окна'
        self.main_window = main_window

        self.obj_to_edit = obj_to_edit

        self.setWindowFlags(Qt.WindowType.Popup)
        self.setObjectName("calendarFrame")
        self.setStyleSheet("""
            QWidget {
                background: white;
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

    def update_view(self):
        for btn in self.day_buttons:
            btn.deleteLater()
        self.day_buttons.clear()

        self.month_year_label.setText(
            f"{months[self.pick_date.month - 1][2].capitalize()} {self.pick_date.year}"
        )

        from_day = self.pick_date - timedelta(days=self.pick_date.weekday())

        for index in range(6*7):
            day = from_day + timedelta(days=index)
            is_current_month = day.month == self.pick_date.month

            btn = SegmentedButton(day, is_today=day == date.today(), is_bold=is_current_month)

            tooltips = []
            colors = []
            for event in self.main_window.scheduled_events:
                event: ScheduleEvent
                if not event.can_happen(day): continue
                colors.append(QColor(*event.color))
                tooltips.append(event.name)

            if tooltips: btn.setToolTip("\n".join(tooltips))
            btn.set_colors(colors)

            # noinspection PyUnresolvedReferences
            btn.clicked.connect(lambda _, d=day: self.date_selected(d))

            self.grid_layout.addWidget(btn, *divmod(index + 7, 7))
            self.day_buttons.append(btn)

    def date_selected(self, day):
        # noinspection PyUnresolvedReferences
        self.obj_to_edit.setText(beauty_date(day))
        self.hide()

    def cycle(self, offset):
        self.pick_date = self.pick_date.replace(month=self.pick_date.month + offset)
        self.update_view()


class SegmentedButton(QPushButton):
    def __init__(self, day: date, is_today, is_bold, colors=None, parent=None):
        super().__init__(str(day.day))
        self.setParent(parent)
        self.colors = colors or []
        self.setFixedSize(30, 30)

        self.is_today = is_today
        self.is_bold = is_bold

        self.setStyleSheet(
        """
            SegmentedButton {
                border: 3px solid #0078d4;
                border-radius: 5px;
                background: rgba(0, 120, 212, 0.8);
                color: black;
                font-weight: bold;
            }
            SegmentedButton:hover {
                background: rgba(0, 120, 212, 0.9);
            }
        """
            if is_today else
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
        if not self.colors or self.is_today:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        offset = 2
        rect = QRectF(offset, offset, self.width() - offset * 2, self.height() - offset * 2)

        angle_offset = len(self.colors) * 45 - 45 if 1 <= len(self.colors) <= 2 else 0
        angle = 360.0 / len(self.colors)

        painter.setPen(QColor(0, 0, 0, 0))
        for i, color in enumerate(self.colors):
            color.setAlpha(120)
            painter.setBrush(color)
            painter.drawPie(rect, int(i * angle * 16 + angle_offset * 16), int(angle * 16))

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

        all_sorted = sorted(((e, e.get_next_date(datetime.now().date())[0]) for e in events),
                            key=lambda x: x[0].get_sort_value() if x[1] is None else x[1].timestamp())

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
        now = self.app.get_now()
        def tracking(event: ScheduleEvent):
            start_date, end_date = event.get_next_date(now)
            if start_date is None or now > end_date: return False
            if event.tags.have(Tags.TRACKING.NO): return False

            if event.tags.have(Tags.IMPORTANT.YES): return True

            if start_date - now > timedelta(days=31): return False

            if event.tags.have(Tags.TRACKING.YES):  return True

            return False

        sorted_events = sorted(
            ((event, event.get_next_date(now)[0]) for event in events if tracking(event)),
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

            start_date, end_date = event.get_next_date(now)
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