import json
import os
from datetime import datetime, date
from math import atan2, sin, cos, radians, ceil

from PyQt6.QtCore import Qt, QSize, QRect, QPoint, QTimer
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QFontDatabase, QAction, QStandardItem, \
    QStandardItemModel
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QFrame, QGridLayout, QGraphicsDropShadowEffect, QSlider,
    QLineEdit, QVBoxLayout, QScrollArea, QTextEdit, QApplication, QComboBox
)

from announced_task import AnnouncedTask
from tags import Tags, Tag
from utils import days_of_week, months, ScheduleEvent, rgb_to_hex, str_time, interpolate, beauty_time

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

def simple_tray_action(parent, name, callback=None):
    action = QAction(name, parent)

    if callback: # noinspection PyUnresolvedReferences
        action.triggered.connect(callback)
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

def new_separator(w=None, h=None, col="#000000"):
    separator = QFrame()
    if w is not None: separator.setFixedWidth(w)
    if h is not None: separator.setFixedHeight(h)
    separator.setStyleSheet(f"background-color: {col};")
    return separator

def ui_shadow(element):
    shadow_effect = QGraphicsDropShadowEffect()
    shadow_effect.setBlurRadius(5)
    shadow_effect.setOffset(2, 2)
    shadow_effect.setColor(QColor(0, 0, 0, 160))
    element.setGraphicsEffect(shadow_effect)

def draw_arrow(painter: QPainter, length, arrow_angle, x1, y1, x2=None, y2=None, arrow1=True, arrow2=True):
    if x2 is None: x2 = x1
    if y2 is None: y2 = y1
    angle = atan2(y2 - y1, x2 - x1)

    painter.drawLine(x1, y1, x2, y2)
    if arrow1:
        painter.drawLine(x1, y1,
                         int(x1 + cos(angle + radians(arrow_angle - 180)) * length),
                         int(y1 - sin(angle + radians(arrow_angle - 180)) * length))
        painter.drawLine(x1, y1,
                         int(x1 + cos(angle - radians(arrow_angle - 180)) * length),
                         int(y1 - sin(angle - radians(arrow_angle - 180)) * length))
    if arrow2:
        painter.drawLine(x2, y2,
                         int(x2 + cos(angle + radians(arrow_angle)) * length),
                         int(y2 - sin(angle + radians(arrow_angle)) * length))
        painter.drawLine(x2, y2,
                         int(x2 + cos(angle - radians(arrow_angle)) * length),
                         int(y2 - sin(angle - radians(arrow_angle)) * length))

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


class SpoilerOptions(QPushButton):
    def __init__(self, name: str, widgets: list[QWidget] = None, collapsed=True):
        super().__init__(name)

        self.shown = True
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
        if collapsed: self.hide_all()

    def setWidgets(self, widgets):
        self.widgets = widgets

    def on_click(self):
        if self.shown:
            self.hide_all()
        else:
            self.show_all()

    def hide_all(self):
        self.shown = False

        for widget in self.widgets: widget.hide()

    def show_all(self):
        self.shown = True

        for widget in self.widgets: widget.show()


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
        self.setMinimumHeight(590)

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

        self.selected_weekdays = []
        self.selected_monthdays = []
        self.selected_months = []
        self.selected_years = []

        self.weekdays_btns:  list[SlideButton] = []
        self.monthdays_btns: list[SlideButton] = []
        self.months_btns:    list[SlideButton] = []
        self.years_btns:     list[SlideButton] = []

        self.title = simple_label("Новое условие", 20, "Times New Roman")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.title)
        self.create_ui_switch()
        self.create_ui_weekday_select()
        self.create_ui_monthday_select()
        self.create_ui_month_select()
        self.create_ui_year_select()
        self.create_ui_weekparity()
        self.create_ui_time_select()
        self.layout.addStretch(0)
        self.setLayout(self.layout)

        self.is_weekday = False
        self.set_to_weekday()

        self.parity = 0
        self.change_week_parity(0)

        self.delete_button = icon_button("remove.svg", 50, 70, 'red',
                                         callback=self.remove, parent=self)

        self.clone_button  = icon_button("add.svg", 50, 70, 'blue',
                                         callback=self.clone_self, parent=self)

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

    def setup_values(self, weekdays, monthdays, months, years):
        for btns, compares in [
            [self.weekdays_btns,  weekdays],
            [self.monthdays_btns, monthdays],
            [self.months_btns,    months],
            [self.years_btns,     years]
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

        self.weekday_select_container.setVisible(True)
        self.monthday_select_container.setHidden(True)

    def set_to_monthday(self):
        if not self.is_weekday: return
        self.is_weekday = False

        self.btn_weekday.setStyleSheet(self.off_style)
        self.btn_monthday.setStyleSheet(self.on_style)

        self.weekday_select_container.setHidden(True)
        self.monthday_select_container.setVisible(True)

    def create_ui_switch(self):
        layout = QHBoxLayout()

        slash = simple_label("/", 20)
        slash.setStyleSheet("color: black; border: none;")

        self.btn_weekday = simple_button(
            "День недели", "calibri", 15, None, 0, callback=self.set_to_weekday)

        self.btn_monthday = simple_button(
            "День месяца", "calibri", 15, None, 0, callback=self.set_to_monthday)

        for btn in (self.btn_weekday, self.btn_monthday):
            btn.setFixedSize(140, 40)

        layout.addWidget(self.btn_weekday)
        layout.addWidget(slash)
        layout.addWidget(self.btn_monthday)

        layout.addWidget(icon_button("calendar.svg", 50, 60, 'yellow',
                                     callback=self.set_current_date, icon_color=(0, 0, 0)))

        layout.addStretch(0)

        self.layout.addLayout(layout)

    def create_ui_weekday_select(self):
        self.weekday_select_container = QWidget()
        self.weekday_select_container.setFixedHeight(150)
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

    def create_ui_month_select(self):
        self.month_select_container = QWidget()
        self.month_select_container.setFixedHeight(110)
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

        layout.addWidget(simple_label("Чётность недели - ", 30))
        layout.addWidget(self.parity_button)
        layout.addStretch(0)
        self.layout.addLayout(layout)

    def create_ui_time_select(self):
        self.time_selector = TimeSelector(8, 24)
        self.layout.addWidget(self.time_selector)

    def clone_self(self):
        clone = DateSelector(self.parent)
        clone.setup_values(self.selected_weekdays, self.selected_monthdays, self.selected_months, self.selected_years)
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

        for btn in [self.delete_button, self.clone_button]:
            btn.move(self.width() - start_pos - btn.width(), 10)
            start_pos += btn.width() + between_offset


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
            if not task.do_expire:
                self.before_type_combo.setCurrentIndex(0) # за N минут
            else:
                self.before_type_combo.setCurrentIndex(1) # N мин. / после
        else:
            self.before_type_combo.setCurrentIndex(2) # Если просрочено

        self.before_minutes_input.setText(str(max(0, task.delay)))
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
        try:
            if ensure_time: minutes = int(self.before_minutes_input.text())
        except ValueError:
            raise AssertionError('Укажи кол-во минут перед задачей')

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

    # noinspection PyUnresolvedReferences
    def set_events(self, events: list[ScheduleEvent]):
        for i in range(self.events_layout.count()):
            w = self.events_layout.itemAt(i).widget()
            w.deleteLater()

        for event in sorted(events, key=lambda e: e.date.get_sort_value() + e.times * 10000):
            btn = EventButton(event)

            # noinspection PyUnresolvedReferences
            def on_click(button: EventButton):
                self.app.create_task_add_form(button.event)
                self.setHidden(True)

            btn.set_on_click(on_click)
            self.events_layout.addWidget(btn)

        self.events_scroll.verticalScrollBar().setValue(0)
        self.setVisible(True)


class UpcomingEvents(QFrame):
    def __init__(self, parent):
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
        self.toggle_btn = icon_button(
            "up.svg", 0, 90, 'blue',
            callback=self.toggle_view
        )
        self.toggle_btn.setFixedSize(50, 70)

        self.main_layout = QVBoxLayout()

        self.sub_layout = QHBoxLayout()
        self.sub_layout.addWidget(self.toggle_btn)

        self.main_layout.addLayout(self.sub_layout)
        self.main_layout.addWidget(self.events_scroll)
        self.main_layout.addStretch(0)

        self.setLayout(self.main_layout)
        self.setFixedWidth(300)

        self.timer = QTimer(self)
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.update_timers)
        self.timer.start(1000)

        self.toggle_view()

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

        for i in range(1, self.sub_layout.count()):
            w = self.sub_layout.itemAt(i).widget()
            w.deleteLater()

        for i in range(self.events_layout.count()):
            w = self.events_layout.itemAt(i).widget()
            w.deleteLater()

        def tracking(event: ScheduleEvent):
            # noinspection PyUnresolvedReferences
            if event.get_next_date(self.app.get_now()) is None: return False
            if event.tags.have(Tags.TRACKING.NO): return False

            if event.tags.have(Tags.IMPORTANT.YES): return True
            if event.tags.have(Tags.TRACKING.YES):  return True

            return False

        # noinspection PyUnresolvedReferences
        sorted_events = sorted(
            ((event, event.get_next_date(self.app.get_now())) for event in events if tracking(event)),
            key=lambda x: x[1])

        if not sorted_events:
            return self.setHidden(True)
        self.setVisible(True)

        prev_date = None
        for i, (event, next_date) in enumerate(sorted_events):
            if next_date is None: continue
            btn = EventButton(event, second_label=True)
            btn.set_on_click_editor(self.app)

            self.events.append(event)
            self.events_buttons.append(btn)
            if i == 0:
                btn.setFixedHeight(70)
                self.sub_layout.addWidget(btn)
            else:
                if prev_date != next_date.date() and prev_date is not None:
                    self.events_layout.addWidget(new_separator(h=4))
                self.events_layout.addWidget(btn)
                prev_date = next_date.date()

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

            next_date = event.get_next_date(now)
            if next_date is None: return self.update_events(self.events.copy())

            prefix = "" if i == 0 else "Остаётся: "
            subtitle = f'{prefix}{beauty_time(ceil((next_date - now).total_seconds() / 60))}'

            button.lb_subtitle.setText(subtitle)

            if i == 0: first_day = next_date
            else:
                if next_date.date() == first_day.date():
                    more_events += 1

        if more_events > 0:
            self.events_buttons[0].lb_subtitle.setText(
                f'{beauty_time(ceil((first_day - now).total_seconds() / 60))} (+{more_events})'
            )


class EventButton(QPushButton):
    def __init__(self, event: ScheduleEvent, override_important=None, second_label=False):
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