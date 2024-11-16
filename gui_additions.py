from datetime import datetime, date

from PyQt6.QtCore import Qt, QSize, QRect, QPoint
from PyQt6.QtGui import QColor, QFont, QIcon, QPixmap, QPainter, QPen, QFontDatabase, QAction
from PyQt6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QPushButton, QFrame, QGridLayout, QGraphicsDropShadowEffect, QSlider,
    QLineEdit, QVBoxLayout, QScrollArea, QTextEdit
)

from tags import Tags, Tag
from utils import days_of_week, months, ScheduleEvent, rgb_to_hex, str_time

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

def set_custom_color_scheme(element, r, g, b, hover_offset=40, click_offset=-40, border_offset=-20):
    col_rgb = QColor.fromRgb(r, g, b)
    h = col_rgb.hue()
    s = col_rgb.saturation()
    v = col_rgb.value()
    col1 = rgb_to_hex(QColor.fromHsv(h, s, v).getRgb())
    col2 = rgb_to_hex(QColor.fromHsv(h, s, max(0, min(255, v + hover_offset))).getRgb())
    col3 = rgb_to_hex(QColor.fromHsv(h, s, max(0, min(255, v + click_offset))).getRgb())
    col4 = rgb_to_hex(QColor.fromHsv(h, s, max(0, min(255, v + border_offset))).getRgb())

    element.setStyleSheet(f"""
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

    def set_min(self, new_min): self.current_min = max(self.min_value, new_min)
    def set_max(self, new_max): self.current_max = min(self.max_value, new_max)

    @staticmethod
    def get_timestr(value, leading_zero=True):
        return str_time(value * 10, leading_zero=leading_zero)

    def get_timedur(self):
        return f'{self.get_timestr(self.current_min)}-{self.get_timestr(self.current_max)}'

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        self.paint_background(painter)
        self.paint_between(painter)
        self.paint_marker('min', painter, QColor(50, 100, 200), self.value_to_position(self.current_min))
        self.paint_marker('max', painter, QColor(200, 50,  50), self.value_to_position(self.current_max))
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
        x1 = self.value_to_position(self.current_min)
        x2 = self.value_to_position(self.current_max)
        y  = (self.height() - self.slider_height) // 2
        offset = 8
        painter.setPen(QPen(QColor(255, 255, 255), 8))
        painter.drawRect(QRect(
            x1      + 1, y                  + offset,
            x2 - x1 - 2, self.slider_height - offset * 2
        ))

    def paint_duration(self, painter: QPainter):
        x = (self.value_to_position(self.current_min) + self.value_to_position(self.current_max)) // 2

        painter.setPen(QColor(0, 0, 0))
        f = painter.font()
        f.setPointSize(10)
        f.setBold(True)
        painter.setFont(f)

        painter.drawText(x - 14, self.height() // 2 + 5, self.get_timestr(self.current_max - self.current_min, False))

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


class DateSelector(QFrame):
    def __init__(self, parent, i=0, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setParent(parent)
        self.parent = parent
        self.setStyleSheet(f'background-color: {"#d4d4d4" if i % 2 else "#d9d9d9"};')
        self.setMinimumHeight(550)

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

        self.selected_weekdays = []
        self.selected_monthdays = []
        self.selected_months = []

        self.weekdays_btns:  list[SlideButton] = []
        self.monthdays_btns: list[SlideButton] = []
        self.months_btns:    list[SlideButton] = []

        self.setObjectName("dateSelectorBorder")

        self.title = simple_label("Новое условие", 20, "Times New Roman")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.title)
        self.create_ui_switch()
        self.create_ui_weekday_select()
        self.create_ui_monthday_select()
        self.create_ui_month_select()
        self.create_ui_weekparity()
        self.create_ui_time_select()
        self.layout.addStretch(0)
        self.setLayout(self.layout)

        self.is_weekday = False
        self.set_to_weekday()

        self.parity = 0
        self.change_week_parity(0)

        self.delete_button = icon_button("remove.svg", 50, 70, 'red',
                                         callback=self.deleteLater, parent=self)

        self.clone_button  = icon_button("add.svg", 50, 70, 'blue',
                                         callback=self.clone_self, parent=self)

    def set_current_date(self):
        if self.is_weekday: self.set_to_monthday()

        now = datetime.now()
        for compare, btns in [
            [now.day,   self.monthdays_btns],
            [now.month, self.months_btns]
        ]:
            for btn in btns: btn.setState(btn.value == compare)

    def setup_values(self, weekdays, monthdays, months):
        for btns, compares in [
            [self.weekdays_btns,  weekdays],
            [self.monthdays_btns, monthdays],
            [self.months_btns,    months]
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
        clone.setup_values(self.selected_weekdays, self.selected_monthdays, self.selected_months)
        clone.change_week_parity(self.parity)

        clone.time_selector.set_min(self.time_selector.current_min)
        clone.time_selector.set_max(self.time_selector.current_max)

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
            if event.tags.have(Tags.IMPORTANT.YES):
                btn = simple_button(event.name, "calibri", 20, bold=True)
                set_custom_color_scheme(btn, *event.color, border_offset=-255)
            else:
                btn = simple_button(event.name, "calibri", 20)
                set_custom_color_scheme(btn, *event.color)
            btn.setFixedHeight(50)

            # noinspection PyUnresolvedReferences
            def on_click(_, event=event):
                self.app.create_task_add_form(event)
                self.setHidden(True)

            btn.clicked.connect(on_click)
            self.events_layout.addWidget(btn)

        self.events_scroll.verticalScrollBar().setValue(0)
        self.setVisible(True)
