import math

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QColor, QConicalGradient, QPainter, QGradient, QPen
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout


class GradientWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Conic Gradient Example")
        self.setGeometry(100, 100, 400, 400)
        self.colors = [QColor('red'), QColor('blue'), QColor('green'), QColor('orange'), QColor('purple')]

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.colors:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Рисуем сектора
        rect = QRectF(3, 3, self.width() - 6, self.height() - 6)
        total = len(self.colors)
        angle = 360.0 / total

        for i, color in enumerate(self.colors):
            painter.setBrush(color)
            painter.setPen(QPen(color, 2))
            painter.drawPie(rect, int(i * angle * 16), int(angle * 16))

        # Рисуем разделители
        painter.setPen(QPen(Qt.GlobalColor.black, 3))
        for i in range(0, total):
            angle_deg = i * angle - 0
            x = self.width() / 2 + (self.width() / 2 - 2) * math.cos(math.radians(angle_deg))
            y = self.height() / 2 + (self.height() / 2 - 2) * math.sin(math.radians(angle_deg))
            painter.drawLine(*map(round, (self.width() / 2, self.height() / 2, x, y)))


if __name__ == "__main__":
    app = QApplication([])
    window = GradientWidget()
    window.show()
    app.exec()
