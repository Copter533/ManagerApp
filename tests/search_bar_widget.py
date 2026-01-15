import os
import re
from typing import Optional, Tuple, List
from PyQt6.QtCore import Qt, QRectF, pyqtSignal, QTimer
from PyQt6.QtGui import QPainter, QFont, QColor
from PyQt6.QtWidgets import (QApplication, QWidget, QVBoxLayout,
                             QMainWindow, QLineEdit, QScrollArea, QFrame)

from date_utils import Config
from gui_additions import LayoutBuilder, EventButton, new_separator, load_font
from tags import Tags


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


class SearchBarWidget(QLineEdit):
    searchChanged = pyqtSignal(str)

    def __init__(self, scroll_container=None, allowed_chars: str = "-_+="):
        super().__init__()
        self.scroll_container = scroll_container

        self.font_anonymous = load_font("AnonymousPro.ttf")
        self.font_evo_sans = load_font("EvoSans.otf")

        font = QFont(self.font_anonymous, 30)
        self.setFont(font)

        self.elements_data = []
        self.found_matches = 0
        self.allowed_chars = allowed_chars

        self.textChanged.connect(self._on_text_change)

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

    def _on_text_change(self, new_text: str):
        if not self.scroll_container:
            return

        cleaned_query = SearchBarWidget.clean_string(new_text, self.allowed_chars)

        if not cleaned_query:
            for widget, _, _, _, _ in self.elements_data:
                widget.show()
            self.found_matches = len(self.elements_data)
            self._restore_order()
        else:
            visible_indices = []
            self.found_matches = 0

            for idx, (widget, _, keywords, cleaned_name, cleaned_keywords) in enumerate(self.elements_data):
                if cleaned_name:
                    name_words = cleaned_name.strip(" ").split(" ")
                    name_similarity = min(SearchBarWidget.calculate_similarity_with_layouts(
                        cleaned_query, name_word
                    ) for name_word in name_words)

                    if cleaned_query == cleaned_name:
                        name_similarity = -10000
                else:
                    name_similarity = 10000

                if new_text.count("-") == len(new_text):
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

                visible = min_similarity <= len(cleaned_query) * 2

                if visible:
                    widget.show()
                    self.found_matches += 1
                    visible_indices.append((idx, min_similarity))
                else:
                    widget.hide()

            if visible_indices:
                visible_indices.sort(key=lambda x: x[1])
                self._reorder_by_visibility(visible_indices)
            else:
                self.scroll_container._update_container()

        self.update()

    def _restore_order(self):
        order = list(range(len(self.elements_data)))
        if self.scroll_container:
            self.scroll_container.reorder(order)

    def _reorder_by_visibility(self, visible_indices_with_similarity):
        visible_indices = [idx for idx, _ in visible_indices_with_similarity]

        all_indices = list(range(len(self.elements_data)))
        new_order = visible_indices + [idx for idx in all_indices if idx not in visible_indices]

        if self.scroll_container:
            self.scroll_container.reorder(new_order)

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

    def add_search_element(self, widget, name, keywords=None):
        cleaned_name = SearchBarWidget.clean_string(name, self.allowed_chars)
        cleaned_keywords = [SearchBarWidget.clean_string(kw, self.allowed_chars)
                            for kw in (keywords or [])]

        self.elements_data.append((widget, name, keywords or [], cleaned_name, cleaned_keywords))

        if self.scroll_container:
            self.scroll_container.addWidget(widget)

    def add_search_elements(self, widgets, func):
        for widget in widgets:
            self.add_search_element(widget, *func(widget))


class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Поиск по событиям")
        self.setGeometry(100, 100, 450, 450)
        self.setStyleSheet("background-color: #FFFFFF; color: black;")

        os.chdir("../")
        events = Config.load("schedule_v2.json").events

        scroll_area = ReorderableScrollArea()

        search_bar = SearchBarWidget(scroll_area, allowed_chars="-_:+=")

        btns = [EventButton(event) for event in events]
        search_bar.add_search_elements(btns, lambda e: (e.event.name, None))

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