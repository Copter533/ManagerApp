import os
import re
from typing import Optional, Tuple, List, Callable, Any
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer, QPoint, QSize
from PyQt6.QtGui import QPainter, QFont, QColor, QAction, QIcon
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QMainWindow, QLineEdit, QScrollArea, QFrame,
                             QComboBox, QLabel, QPushButton, QSizePolicy, QHBoxLayout, QLayout, QGridLayout)

from date_utils import Config
from gui_additions import LayoutBuilder, EventButton, new_separator, load_font, icon_button, simple_label, \
    simple_combo_box, recolor_icon, set_color_scheme
from multidate_v2 import MultiDateMixer
from tags import Tags
from utils import DebugTimer


class AdvancedOptionsPopup(QFrame):
    """Всплывающее окно с дополнительными опциями поиска"""

    def __init__(self, layout, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.set_elements_layout(layout)

    def set_elements_layout(self, layout):
        self.layout: QLayout = layout

        self.container = QWidget()
        self.container.setObjectName("popupContainer")
        self.container.setStyleSheet("""
                    #popupContainer {
                    color: red;
                        background-color: white;
                        border-radius: 10px;
                        border: 2px solid #ccc;
                        padding: 15px;
                    }
                """)

        self.container.setLayout(self.layout)
        self.setLayout(LayoutBuilder(QVBoxLayout).addWidget(self.container).build())

    def show_at_position(self, pos: QPoint):
        self.move(pos)
        self.show()
        self.raise_()


class ReorderableScrollArea(QScrollArea):
    def __init__(self):
        super().__init__()
        self.container = QWidget()
        self.layout = QVBoxLayout(self.container)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self.setWidget(self.container)
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)

        self._widgets = []
        self._order = []

    def addWidget(self, widget):
        self._widgets.append(widget)
        self._order.append(len(self._widgets) - 1)
        self.layout.addWidget(widget)
        self._update_container()

    def insertWidget(self, index, widget):
        self._widgets.insert(index, widget)
        self._order.insert(index, index)

        for i in range(len(self._order)):
            if self._order[i] >= index and i != index:
                self._order[i] += 1

        self._reapply_layout()

    def removeWidget(self, widget):
        if widget in self._widgets:
            idx = self._widgets.index(widget)
            self._widgets.remove(widget)

            order_idx = self._order.index(idx)
            self._order.pop(order_idx)

            for i in range(len(self._order)):
                if self._order[i] > idx:
                    self._order[i] -= 1

            widget.setParent(None)
            self._reapply_layout()

    def reorder(self, new_order):
        if len(new_order) != len(self._widgets):
            return False

        if sorted(new_order) != list(range(len(self._widgets))):
            return False

        self._order = new_order.copy()
        self._reapply_layout()
        return True

    def _reapply_layout(self):
        while self.layout.count():
            item = self.layout.takeAt(0)

        for idx in self._order:
            widget = self._widgets[idx]
            self.layout.addWidget(widget)

        self._update_container()

    def _update_container(self):
        self.container.adjustSize()
        self.container.updateGeometry()
        QTimer.singleShot(10, self._force_update)

    def _force_update(self):
        self.updateGeometry()
        self.viewport().update()

    def widgets(self):
        return self._widgets.copy()

    def clear(self):
        for widget in self._widgets:
            widget.deleteLater()
        self._widgets.clear()
        self._order.clear()
        self._update_container()


class SearchLineEdit(QLineEdit):
    """Компонент строки поиска"""

    filterChanged = pyqtSignal()

    def __init__(self, parent: "SearchBarWidget"):
        super().__init__()
        self.font_anonymous = load_font("AnonymousPro.ttf")
        self.font_evo_sans = load_font("EvoSans.otf")

        font = QFont(self.font_anonymous, 30)
        self.setFont(font)

        self.found_matches = 0
        self.search_bar = parent

        self.textChanged.connect(self.filterChanged)

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(QFont(self.font_evo_sans, 20))

        w = self.width()
        h = self.height()

        color = QColor(0, 0, 0, 100)
        text = "..."

        if self.text():
            color = QColor(0, 0, 0, 100) if self.found_matches > 0 else QColor(255, 0, 0, 150)
            text = str(self.found_matches)

            if not self.search_bar.clean_string(self.text()) and "-" not in self.text():
                color = QColor(255, 0, 0, 150)
                text = "???"

        painter.setPen(color)
        text_rect = QRectF(w / 2, 0, w / 2, h)
        painter.drawText(
            text_rect,
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
            text
        )

    def update_match_count(self, count: int):
        """Обновляет счетчик найденных элементов"""
        self.found_matches = count
        self.update()


class SearchBarWidget(QWidget):
    filterChanged = pyqtSignal()

    def __init__(self, scroll_container=None, allowed_chars: str = "-_+=",
                 advanced_options: Callable[
                     [Callable],
                     tuple[
                         Callable[[Any, str, str, float], float | int | None],
                         QLayout
                     ]
                 ] = None):
        """
        :param advanced_options:
            Необязательная фабрика расширенных опций поиска.

            Callable вида:
                advanced_options(on_change) -> (filter_fn, layout)

            где filter_fn(widget, query, cleaned_name, score)
            возвращает новое значение score или None,
            а layout — QLayout для всплывающего окна опций.
        """
        super().__init__()
        self.scroll_container = scroll_container
        self.options_filter, self.options_layout = (None, None) if advanced_options is None else advanced_options(self._on_filter_change)
        self.options_fabric = advanced_options

        self.font_anonymous = load_font("AnonymousPro.ttf")
        self.font_evo_sans = load_font("EvoSans.otf")

        self.elements_data = []  # [(widget, name, keywords, cleaned_name, cleaned_keywords, event_obj), ...]
        self.found_matches = 0
        self.allowed_chars = allowed_chars

        self._setup_ui()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Верхняя строка: поле поиска + кнопка опций
        top_row = QWidget()
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(5)

        # Кнопка сброса и нового поиска
        self.btn_reset_search = icon_button(
            "remove.svg", 40, 50, 'red',
            callback=self._reset_search
        )
        top_row_layout.addWidget(self.btn_reset_search)

        # Поле ввода поиска
        self.search_input = SearchLineEdit(self)
        self.search_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.search_input.filterChanged.connect(self._on_filter_change)
        top_row_layout.addWidget(self.search_input)

        # Кнопка дополнительных опций
        if self.options_layout:
            self.options_button = icon_button(
                "gear.svg", 40, 50, 'white', icon_color=(0, 0, 0),
                callback=self._show_advanced_options
            )
            self.options_button.setCheckable(True)

            top_row_layout.addWidget(self.options_button)

            # Всплывающее окно дополнительных опций
            self.advanced_popup = AdvancedOptionsPopup(self.options_layout, self)
            self.advanced_popup.hide()

            # Таймер для проверки кликов вне окна
            self.click_outside_timer = QTimer(self)
            self.click_outside_timer.timeout.connect(self._check_click_outside)
            self.click_outside_timer.start(100)

        main_layout.addWidget(top_row)

    def _reset_search(self):
        """Показывает всплывающее окно с дополнительными опциями"""
        if self.options_fabric:
            self.advanced_popup.deleteLater()
            self.options_filter, layout = self.options_fabric(self._on_filter_change)
            self.advanced_popup = AdvancedOptionsPopup(layout, self)
            self._show_advanced_options()
            self._on_filter_change()

        self.search_input.setText("")
        self.search_input.setFocus()

    def _show_advanced_options(self):
        """Показывает всплывающее окно с дополнительными опциями"""
        if self.options_button.isChecked():
            # Позиционируем окно рядом с кнопкой
            btn_global_pos = self.options_button.mapToGlobal(QPoint(0, 0))
            popup_x = btn_global_pos.x() + self.options_button.width() + 5
            popup_y = btn_global_pos.y()

            self.advanced_popup.show_at_position(QPoint(popup_x, popup_y))
        else:
            self.advanced_popup.hide()

    def _check_click_outside(self):
        """Проверяет, был ли клик вне всплывающего окна"""
        if self.advanced_popup.isVisible() and not self.options_button.isChecked():
            self.advanced_popup.hide()

    def _on_filter_change(self):
        """Обработчик изменения любых фильтров"""
        self._apply_filters()

    @staticmethod
    def get_key_coords(char: str) -> tuple[int, int] | tuple[None, None]:
        target = char.lower()

        if ord("а") <= ord(target) <= ord("я"):
            keyboard_layout = [
                "йцукенгшщзхъ",
                "фывапролджэ",
                "ячсмитьбю"
            ]
        elif ord("a") <= ord(target) <= ord("z"):
            keyboard_layout = [
                "qwertyuiop",
                "asdfghjkl",
                "zxcvbnm"
            ]
        else:
            return None, None

        for y, keyboard_line in enumerate(keyboard_layout):
            x = keyboard_line.find(target)
            if x != -1:
                return x, y
        return None, None

    @staticmethod
    def is_key_close(char1: str, char2: str) -> bool:
        x1, y1 = SearchBarWidget.get_key_coords(char1)
        x2, y2 = SearchBarWidget.get_key_coords(char2)
        if x1 is None or x2 is None:
            return False

        if y1 == y2 and abs(x1 - x2) <= 1:
            return True
        if abs(y1 - y2) <= 1 and x1 == x2:
            return True
        return False

    @staticmethod
    def keyboard_distance(str1: str, str2: str,
                          cost_insert: float = 1.0,
                          cost_delete: float = 1.0,
                          cost_replace: int = 2,
                          cost_nearby: int = 2,
                          cost_transpose: float = 0.5) -> float:
        str1 = str1.lower()
        str2 = str2.lower()

        if len(str1) > len(str2):
            str1, str2 = str2, str1

        n, m = len(str1), len(str2)
        dp = [[0.0] * (n + 1) for _ in range(m + 1)]

        for i in range(1, m + 1):
            dp[i][0] = dp[i - 1][0] + cost_delete
        for j in range(1, n + 1):
            dp[0][j] = dp[0][j - 1] + cost_insert

        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if str2[i - 1] == str1[j - 1]:
                    replace_cost = 0.0
                elif SearchBarWidget.is_key_close(str2[i - 1], str1[j - 1]):
                    replace_cost = cost_nearby
                else:
                    replace_cost = cost_replace

                dp[i][j] = min(
                    dp[i - 1][j] + cost_delete,
                    dp[i][j - 1] + cost_insert,
                    dp[i - 1][j - 1] + replace_cost
                )

                if i > 1 and j > 1 and str2[i - 1] == str1[j - 2] and str2[i - 2] == str1[j - 1]:
                    dp[i][j] = min(dp[i][j], dp[i - 2][j - 2] + cost_transpose)

        return dp[m][n]

    def clean_string(self, text: str) -> str:
        pattern = f"[^a-zA-Zа-яА-Я0-9\\s{re.escape(self.allowed_chars)}]"
        return re.sub(pattern, "", text).lower()

    @staticmethod
    def translate_layout(text: str) -> str:
        layout_mapping = {
            'q': 'й', 'w': 'ц', 'e': 'у', 'r': 'к', 't': 'е', 'y': 'н',
            'u': 'г', 'i': 'ш', 'o': 'щ', 'p': 'з', '[': 'х', ']': 'ъ',
            'a': 'ф', 's': 'ы', 'd': 'в', 'f': 'а', 'g': 'п', 'h': 'р',
            'j': 'о', 'k': 'л', 'l': 'д', ';': 'ж', "'": 'э',
            'z': 'я', 'x': 'ч', 'c': 'с', 'v': 'м', 'b': 'и', 'n': 'т',
            'm': 'ь', ',': 'б', '.': 'ю',

            'й': 'q', 'ц': 'w', 'у': 'e', 'к': 'r', 'е': 't', 'н': 'y',
            'г': 'u', 'ш': 'i', 'щ': 'o', 'з': 'p', 'х': '[', 'ъ': ']',
            'ф': 'a', 'ы': 's', 'в': 'd', 'а': 'f', 'п': 'g', 'р': 'h',
            'о': 'j', 'л': 'k', 'д': 'l', 'ж': ';', 'э': "'",
            'я': 'z', 'ч': 'x', 'с': 'c', 'м': 'v', 'и': 'b', 'т': 'n',
            'ь': 'm', 'б': ',', 'ю': '.'
        }

        result = []
        for char in text:
            if char.lower() in layout_mapping:
                mapped = layout_mapping[char.lower()]
                result.append(mapped.upper() if char.isupper() else mapped)
            else:
                result.append(char)

        return ''.join(result)

    @staticmethod
    def calculate_similarity(query: str, target: str) -> float:
        query = query.lower()
        target = target.lower()

        if target.startswith(query):
            prefix_bonus = -100
        elif target.replace(" ", "").startswith(query.replace(" ", "")):
            prefix_bonus = -80
        else:
            prefix_bonus = 0

        base_distance = SearchBarWidget.keyboard_distance(query, target)

        if prefix_bonus == 0 and len(query) >= 3:
            min_len = min(len(query), len(target))
            for i in range(3, min_len + 1):
                if target[:i] == query[:i]:
                    prefix_bonus = -i * 10
                    break

        return base_distance + prefix_bonus

    @staticmethod
    def calculate_similarity_with_layouts(query: str, target: str) -> float:
        original_query = query.lower()
        translated_query = SearchBarWidget.translate_layout(original_query)

        target_lower = target.lower()

        original_similarity = SearchBarWidget.calculate_similarity(original_query, target_lower)
        translated_similarity = SearchBarWidget.calculate_similarity(translated_query, target_lower)

        return min(original_similarity, translated_similarity)

    def _apply_filters(self):
        """Применяет все активные фильтры (текст + дополнительные опции)"""
        if not self.scroll_container:
            return

        text_query = self.search_input.text()
        cleaned_query = self.clean_string(text_query)


        visible_indices = []
        self.found_matches = 0

        for idx, (widget, _, keywords, cleaned_name, cleaned_keywords, event) in enumerate(self.elements_data):
            # Вычисляем релевантность по тексту (если есть запрос)
            if cleaned_query:
                if cleaned_name:
                    name_words = cleaned_name.strip(" ").split(" ")
                    name_distance = min(SearchBarWidget.calculate_similarity_with_layouts(
                        cleaned_query, name_word
                    ) for name_word in name_words)

                    if cleaned_query == cleaned_name:
                        name_distance = -10000
                else:
                    name_distance = 10000

                # Если вместо запроса вписать прочерк, то покажет элементы без имени или с именем из запрещённых символов
                if text_query.count("-") == len(text_query):
                    name_distance = -10000 if not cleaned_name else 10000

                keyword_similarities = []
                if cleaned_keywords:
                    for kw in cleaned_keywords:
                        keyword_similarities.append(
                            SearchBarWidget.calculate_similarity_with_layouts(
                                cleaned_query, kw
                            )
                        )

                min_distance = min([name_distance] + keyword_similarities)
            else:
                min_distance = idx - 10000  # Чтобы не отфильтровали

            if self.options_filter:
                min_distance = self.options_filter(widget, cleaned_query, cleaned_name, min_distance)

            if (min_distance is not None) and (min_distance <= len(cleaned_query) * 2):
                widget.show()
                self.found_matches += 1
                visible_indices.append((idx, min_distance))
            else:
                widget.hide()

        if visible_indices:
            # Сортируем по релевантности (меньше = лучше)
            visible_indices.sort(key=lambda x: x[1])
            self._reorder_by_visibility(visible_indices)
        else:
            # noinspection PyProtectedMember
            self.scroll_container._update_container()

        self.search_input.update_match_count(self.found_matches)
        self.filterChanged.emit()

    def _restore_order(self):
        """Восстанавливает исходный порядок элементов"""
        order = list(range(len(self.elements_data)))
        if self.scroll_container:
            self.scroll_container.reorder(order)

    def _reorder_by_visibility(self, visible_indices_with_similarity):
        """Переупорядочивает элементы по релевантности"""
        visible_indices = [idx for idx, _ in visible_indices_with_similarity]

        all_indices = list(range(len(self.elements_data)))
        new_order = visible_indices + [idx for idx in all_indices if idx not in visible_indices]

        if self.scroll_container:
            self.scroll_container.reorder(new_order)

    def add_search_element(self, widget, name, keywords=None, event=None):
        """Добавляет элемент с предварительной очисткой строк"""
        cleaned_name = self.clean_string(name)
        cleaned_keywords = [self.clean_string(kw)
                            for kw in (keywords or [])]

        self.elements_data.append((widget, name, keywords or [], cleaned_name, cleaned_keywords, event))

        if self.scroll_container:
            self.scroll_container.addWidget(widget)

    def add_search_elements(self, widgets, func):
        for widget in widgets:
            self.add_search_element(widget, *func(widget))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Поиск по событиям ПЛЮС")
        self.setGeometry(100, 100, 450, 450)
        self.setStyleSheet("background-color: #FFFFFF; color: black;")

        os.chdir("../")
        events = Config.load("schedule_v2.json").events

        scroll_area = ReorderableScrollArea()

        def adv_options(on_change):
            base_triple_option = (
                (recolor_icon("clean/any.svg", QColor(100, 100, 100)), "Любое"),
                (recolor_icon("clean/yes.svg", QColor(  0, 255,   0)), "Да"),
                (recolor_icon("clean/no.svg",  QColor(255,   0,   0)), "Нет")
            )

            combo_importance = simple_combo_box(base_triple_option, 20, icon_size=30, on_change=on_change)
            combo_hidden     = simple_combo_box(base_triple_option, 20, icon_size=30, on_change=on_change, current=2)

            # ["Любое", "Бесконечное", "Ограниченное"]
            combo_count_type = simple_combo_box((
                (recolor_icon("clean/any.svg",   QColor(100, 100, 100)), "Любое"),
                (recolor_icon("clean/alarm.svg", QColor(0, 0, 0)), "Бесконечное"),
                (recolor_icon("clean/stop.svg",  QColor(0, 0, 0)), "Ограниченное")),
            20, icon_size=30, on_change=on_change)

            for triple_combo_box in (combo_importance, combo_hidden):
                triple_combo_box.setFixedWidth(150)

            def options_filter(w: EventButton, _, __, score):
                if combo_count_type.currentText() != "Любое":
                    date = w.event.multi_date
                    is_limited = False
                    if w.event.times != 0:
                        is_limited = True
                    else:
                        for subdate in (date.holders if isinstance(date, MultiDateMixer) else [date]):
                            if not (subdate.month_constraint and subdate.year_constraint):
                                break
                        else:
                            is_limited = True

                    if combo_count_type.currentText() != ["Бесконечное", "Ограниченное"][is_limited]:
                        return None

                for combo, ok_tag in (
                    (combo_importance, Tags.IMPORTANT.YES),
                    (combo_hidden,     Tags.HIDDEN.YES),
                ):
                    if combo.currentText() == "Любое":
                        continue
                    if combo.currentText() != ["Нет", "Да"][ok_tag in w.event.tags]:
                        return None

                return score

            header_font = load_font("AnonymousPro.ttf")
            return options_filter, (
                LayoutBuilder(QVBoxLayout)
                # Шапка
                .addWidget(simple_label("Дополнительные", 30,
                                        font=header_font))
                .addSpacing(-10)
                .addWidget(simple_label("параметры", 30,
                                        font=header_font, style="background-color: transparent;"))
                .addSpacing(+10)

                .addWidget(new_separator(h=2))
                .addLayout(
                    LayoutBuilder(QGridLayout)
                    .setCurrentAlignment(Qt.AlignmentFlag.AlignRight)
                    .addWidgetAt(0, 0, simple_label("Важное событие:", 20))
                    .addWidgetAt(0, 1, simple_label("Скрытое событие:", 20))
                    .addWidgetAt(1, 0, combo_importance)
                    .addWidgetAt(1, 1, combo_hidden)
                    .build()
                )
                .addWidget(new_separator(h=2))
                .addWidget(simple_label("Количество выполнений:", 20))
                .addWidget(combo_count_type, alignment=Qt.AlignmentFlag.AlignCenter)
                .addLayout(
                    LayoutBuilder(QHBoxLayout)

                    .build()
                )

                .build()
            )


        search_bar = SearchBarWidget(
            scroll_area, allowed_chars="-_:+=",
            advanced_options=adv_options
        )

        btns = [EventButton(event) for event in events]
        search_bar.add_search_elements(btns, lambda e: (e.event.name, None, e.event))

        self.main_layout = (
            LayoutBuilder(QVBoxLayout)
            .addWidget(search_bar)
            .addWidget(new_separator(h=5))
            .addWidget(scroll_area)
            .build()
        )

        central_widget = QWidget()
        central_widget.setLayout(self.main_layout)
        self.setCentralWidget(central_widget)


if __name__ == "__main__":
    app = QApplication([])
    with DebugTimer("Запуск"):
        window = Window()
        window.show()
    app.exec()