import os
import re
from typing import Optional, Tuple, List
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer, QPoint
from PyQt6.QtGui import QPainter, QFont, QColor
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QMainWindow, QLineEdit, QScrollArea, QFrame,
                             QComboBox, QLabel, QPushButton, QSizePolicy, QHBoxLayout)

from date_utils import Config
from gui_additions import LayoutBuilder, EventButton, new_separator, load_font, icon_button
from tags import Tags


class AdvancedOptionsPopup(QWidget):
    """Всплывающее окно с дополнительными опциями поиска"""

    filterChanged = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.ToolTip |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # Основной контейнер
        self.container = QWidget()
        self.container.setObjectName("popupContainer")
        self.container.setStyleSheet("""
            #popupContainer {
                background-color: white;
                border-radius: 10px;
                border: 2px solid #ccc;
                padding: 15px;
            }
        """)

        layout = QVBoxLayout(self.container)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Секция важности события
        importance_layout = QHBoxLayout()
        importance_layout.addWidget(QLabel("Важное событие?"))

        self.importance_combo = QComboBox()
        self.importance_combo.addItems(["Любое", "Да", "Нет"])
        self.importance_combo.currentIndexChanged.connect(self.filterChanged)

        importance_layout.addWidget(self.importance_combo)
        importance_layout.addStretch()

        layout.addLayout(importance_layout)
        layout.addStretch()

        # Основной layout для окна
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

    def get_importance_filter(self):
        """Возвращает текущее значение фильтра важности"""
        return self.importance_combo.currentText()

    def show_at_position(self, pos: QPoint):
        """Показывает окно в указанной позиции"""
        self.move(pos)
        self.show()
        self.raise_()

    def add_option_widget(self, widget):
        """Добавляет виджет в окно (перед спейсером)"""
        layout = self.container.layout()
        layout.insertWidget(layout.count() - 1, widget)


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

    def __init__(self, allowed_chars: str = "-_+="):
        super().__init__()
        self.font_anonymous = load_font("AnonymousPro.ttf")
        self.font_evo_sans = load_font("EvoSans.otf")

        font = QFont(self.font_anonymous, 30)
        self.setFont(font)

        self.found_matches = 0
        self.allowed_chars = allowed_chars

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
    """Комплексный виджет поиска с дополнительными опциями"""

    filterChanged = pyqtSignal()

    def __init__(self, scroll_container=None, allowed_chars: str = "-_+="):
        super().__init__()
        self.scroll_container = scroll_container

        self.font_anonymous = load_font("AnonymousPro.ttf")
        self.font_evo_sans = load_font("EvoSans.otf")

        self.elements_data = []  # [(widget, name, keywords, cleaned_name, cleaned_keywords, event_obj), ...]
        self.found_matches = 0
        self.allowed_chars = allowed_chars

        self._setup_ui()

        # Подключаем сигналы фильтрации
        self.search_input.filterChanged.connect(self._on_filter_change)
        self.advanced_popup.filterChanged.connect(self._on_filter_change)

    def _setup_ui(self):
        """Настройка пользовательского интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Верхняя строка: поле поиска + кнопка опций
        top_row = QWidget()
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(5)

        # Поле ввода поиска
        self.search_input = SearchLineEdit(self.allowed_chars)
        self.search_input.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        top_row_layout.addWidget(self.search_input)

        # Кнопка дополнительных опций
        self.options_button = icon_button(
            "gear.svg", 40, 40, 'gray', icon_color=(0, 0, 0),
            callback=self._show_advanced_options
        )
        self.options_button.setCheckable(True)
        self.options_button.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                border: 2px solid #d0d0d0;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
            QPushButton:checked {
                background-color: #d0d0d0;
            }
        """)
        top_row_layout.addWidget(self.options_button)

        main_layout.addWidget(top_row)

        # Всплывающее окно дополнительных опций
        self.advanced_popup = AdvancedOptionsPopup(self)
        self.advanced_popup.hide()

        # Таймер для проверки кликов вне окна
        self.click_outside_timer = QTimer(self)
        self.click_outside_timer.timeout.connect(self._check_click_outside)
        self.click_outside_timer.start(100)

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

    @staticmethod
    def clean_string(text: str, allowed_chars: str = None) -> str:
        if allowed_chars is None:
            allowed_chars = "-_+="

        pattern = f"[^a-zA-Zа-яА-Я0-9\\s{re.escape(allowed_chars)}]"
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
        cleaned_query = SearchBarWidget.clean_string(text_query, self.allowed_chars)
        importance_filter = self.advanced_popup.get_importance_filter()

        if not cleaned_query and importance_filter == "Любое":
            for widget, _, _, _, _, _ in self.elements_data:
                widget.show()
            self.found_matches = len(self.elements_data)
            self._restore_order()
        else:
            visible_indices = []
            self.found_matches = 0

            for idx, (widget, _, keywords, cleaned_name, cleaned_keywords, event) in enumerate(self.elements_data):
                # Вычисляем релевантность по тексту (если есть запрос)
                if cleaned_query:
                    if cleaned_name:
                        name_words = cleaned_name.strip(" ").split(" ")
                        name_similarity = min(SearchBarWidget.calculate_similarity_with_layouts(
                            cleaned_query, name_word
                        ) for name_word in name_words)

                        if cleaned_query == cleaned_name:
                            name_similarity = -10000
                    else:
                        name_similarity = 10000

                    if text_query.count("-") == len(text_query):
                        name_similarity = -10000 if not cleaned_name else 10000

                    keyword_similarities = []
                    if cleaned_keywords:
                        for kw in cleaned_keywords:
                            keyword_similarities.append(
                                SearchBarWidget.calculate_similarity_with_layouts(
                                    cleaned_query, kw
                                )
                            )

                    min_similarity = min([name_similarity] + keyword_similarities)
                    text_match = min_similarity <= len(cleaned_query) * 2
                else:
                    # Если нет текстового запроса, считаем что все проходят текст
                    text_match = True
                    min_similarity = 0

                # Фильтр по важности
                importance_match = True
                if importance_filter != "Любое":
                    event_importance = event.tags.get(Tags.IMPORTANT) if hasattr(event, 'tags') else None

                    if importance_filter == "Да":
                        importance_match = event_importance == Tags.IMPORTANT.YES
                    elif importance_filter == "Нет":
                        importance_match = event_importance == Tags.IMPORTANT.NO or event_importance is None

                visible = text_match and importance_match

                if visible:
                    widget.show()
                    self.found_matches += 1
                    visible_indices.append((idx, min_similarity))
                else:
                    widget.hide()

            if visible_indices:
                # Сортируем по релевантности (меньше = лучше)
                visible_indices.sort(key=lambda x: x[1])
                self._reorder_by_visibility(visible_indices)
            else:
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
        cleaned_name = SearchBarWidget.clean_string(name, self.allowed_chars)
        cleaned_keywords = [SearchBarWidget.clean_string(kw, self.allowed_chars)
                            for kw in (keywords or [])]

        self.elements_data.append((widget, name, keywords or [], cleaned_name, cleaned_keywords, event))

        if self.scroll_container:
            self.scroll_container.addWidget(widget)

    def add_search_elements(self, widgets, func):
        for widget in widgets:
            self.add_search_element(widget, *func(widget))

    def add_advanced_option(self, widget):
        """Добавляет виджет в окно дополнительных опций"""
        self.advanced_popup.add_option_widget(widget)


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Поиск по событиям ПЛЮС")
        self.setGeometry(100, 100, 450, 450)
        self.setStyleSheet("background-color: #FFFFFF; color: black;")

        os.chdir("../")
        events = Config.load("schedule_v2.json").events

        scroll_area = ReorderableScrollArea()

        search_bar = SearchBarWidget(scroll_area, allowed_chars="-_:+=")

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
    window = Window()
    window.show()
    app.exec()