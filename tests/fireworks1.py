import sys
import random
import math
from typing import Generator

from PyQt6.QtWidgets import QApplication, QWidget
from PyQt6.QtCore import QTimer, Qt, QPointF, QRectF
from PyQt6.QtGui import QPainter, QColor, QPolygonF
from random import uniform, randint


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 3:
        hex_color = ''.join(c * 2 for c in hex_color)
    # noinspection PyTypeChecker
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def interpolate_color_hex(hex1: str, hex2: str, delta: float):
    r, g, b = interpolate_color_rgb(hex_to_rgb(hex1), hex_to_rgb(hex2), delta)
    return f"#{r:02x}{g:02x}{b:02x}"

def interpolate_color_rgb(rgb1: tuple[int, int, int], rgb2: tuple[int, int, int], delta: float):
    r1, g1, b1 = rgb1
    r2, g2, b2 = rgb2
    r = int((r2 - r1) * delta + r1)
    g = int((g2 - g1) * delta + g1)
    b = int((b2 - b1) * delta + b1)
    return r, g, b

class FireworksWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Фейерверки")
        self.resize(800, 600)

        self._particles = []  # список частиц
        self._rockets   = []    # список ракет

        self.timer = QTimer()
        # noinspection PyUnresolvedReferences
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(10)  # обновление каждые 30 мс

    def launch_rocket(self):
        x = random.uniform(20, self.width() - 20)
        y = self.height()
        vx = random.uniform(-20, 20)
        vy = random.uniform(-300, -200)
        gravity = 100  # ускорение (пикселей/сек^2)
        rocket = Rocket(self, gravity, x, y, vx, vy)
        self._rockets.append(rocket)

    def update_simulation(self):
        dt = 0.01  # шаг времени (сек)

        for particle in is_alive_iterator(self._particles):
            particle.update(dt)

        for rocket in is_alive_iterator(self._rockets):
            rocket: Rocket
            rocket.update(dt)
            if rocket.in_top_point():
                rocket.explode()

        # С вероятностью 2% запускаем новую ракету
        if random.random() < 0.02:
            self.launch_rocket()

        self.update()  # перерисовка виджета

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        for particle in self._particles: particle.draw(painter)
        for rocket   in self._rockets:   rocket.draw()

    def addParticle(self, particle):
        self._particles.append(particle)


class LivingObject:
    def __init__(self, lifetime=None):
        self.age = 0.0
        self.lifetime = lifetime

        self._alive = True

    def update(self, dt):
        if self.lifetime is None: return
        self.age += dt
        if self.age >= self.lifetime:
            self.finish()

    def finish(self): self._alive = False
    def is_alive(self, default_value=True):
        return default_value if self._alive else False


class Particle(LivingObject):
    def __init__(self, processor: FireworksWidget, gravity, x, y, speed, angle, lifetime, color, size=3):
        super().__init__(lifetime)
        self.processor = processor
        self.size = size
        self.x = x
        self.y = y
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)
        self.gravity = gravity

        self.color = color

    def update(self, dt):
        super().update(dt)
        self.age += dt
        if self.age < self.lifetime:
            self.x += self.vx * dt
            self.y += self.vy * dt
            self.vy += self.gravity * dt

    def is_alive(self, **kwargs):
        return super().is_alive(self.age < self.lifetime)

    def draw(self, painter):
        ratio = self.age / self.lifetime
        alpha = max(0, 255 * (1 - ratio))
        color = QColor(self.color.red(), self.color.green(), self.color.blue(), int(alpha))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        painter.drawEllipse(QPointF(self.x, self.y), self.size, self.size)


class TwinkleParticle(Particle):
    def __init__(self, processor: FireworksWidget, gravity, x, y, speed, angle, lifetime, color, size=2):
        super().__init__(processor, gravity, x, y, speed, angle, lifetime, color, size)
        self.particle_tick = 0

    def update(self, dt):
        super().update(dt)

        self.particle_tick = (self.particle_tick + 1) % 2
        if self.particle_tick == 0:
            self.processor.addParticle(
                Particle(self.processor, 0, self.x, self.y, uniform(3, 5), uniform(0, 360), .7,
                             QColor.fromRgb(240, 235, 191), 1))


        if self.age > self.lifetime / 3:
            self.finish()

    def finish(self):
        for n in range(20):
            self.processor.addParticle(
                Particle(self.processor, 0, self.x, self.y, uniform(300, 500), uniform(0, 360), .5,
                         QColor.fromRgb(240, 235, 191), 2)
            )
        super().finish()


class Rocket(LivingObject):
    def __init__(self, processor: FireworksWidget, gravity, x, y, vx, vy):
        super().__init__()
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.gravity = gravity
        self.processor = processor

        self.twinkle = uniform(0, 1) < 0.9

        col = hex_to_rgb(interpolate_color_hex("F0E486", "FFF496", uniform(0, 1)))
        self.trail_color = QColor.fromRgb(*col)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += self.gravity * dt

    def in_top_point(self):
        return self.vy >= -100

    def explode(self):
        if self.twinkle:
            self.explode_twinkle()
        else:
            self.explode_normal()

    def explode_twinkle(self):
        n_particles = random.randint(10, 30)
        base_color = QColor(random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255))
        lifetime = random.uniform(5.5, 6.0)
        for _ in range(n_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 150)
            self.processor.addParticle(
                TwinkleParticle(self.processor, 0, self.x, self.y, speed, angle, lifetime, base_color, 2)
            )
        self.finish()

    def explode_normal(self):
        n_particles = random.randint(50, 100)
        base_color = QColor(random.randint(0, 255),
                            random.randint(0, 255),
                            random.randint(0, 255))
        for _ in range(n_particles):
            angle = random.uniform(0, 2 * math.pi)
            speed = random.uniform(100, 300)
            lifetime = random.uniform(2.0, 5.0)
            self.processor.addParticle(
                Particle(self.processor, self.gravity, self.x, self.y, speed, angle, lifetime, base_color, 4)
            )
        self.finish()

    def draw(self):
        self.processor.addParticle(
            Particle(self.processor, 0,
                     self.x + uniform(-1, 1),
                     self.y + uniform(-1, 1),
                     uniform(0, 40),
                     uniform(-180, 0),
                     .7,
                     self.trail_color))


def is_alive_iterator(elements: list[LivingObject]) -> Generator:
    offset = 0
    for i in range(len(elements)):
        index = i - offset
        element = elements[index]

        if element.is_alive():
            yield element
        if not element.is_alive():
            elements.pop(index)
            offset += 1


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FireworksWidget()
    window.show()
    sys.exit(app.exec())
