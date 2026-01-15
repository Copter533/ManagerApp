import os
import re

from PyQt6.QtGui import QImage, QColor
from PyQt6.QtWidgets import QApplication

void_colors = [
    QColor("transparent")
]


def get_border(image: QImage, swapX=False, swapY=False, swap=False):
    x_range = range(image.width())  if not swapX else range(image.width()  -1, -1, -1)
    y_range = range(image.height()) if not swapY else range(image.height() -1, -1, -1)
    if swap: x_range, y_range = y_range, x_range
    for x in x_range:
        for y in y_range:
            if image.pixelColor(*((y, x) if swap else (x, y))) not in void_colors:
                return x


replacements = {
    "dont_care": "any",
    "checkmark": "yes",
    "remove":    "no",

    "alarm": "alarm",
    "stop": "stop",
}


# Нужно для работы, иначе крашит при вызове чего-угодно Qt-шного
app = QApplication([])
os.makedirs("clean", exist_ok=True)
for file in os.listdir():
    if not file.endswith(".svg"): continue
    new_name = replacements.get(file.replace(".svg", ""))
    if new_name is None: continue
    print(file, "->", new_name)

    image = QImage(file)

    border_size = 5

    left_border   = get_border(image, swapX=False, swap=False) - border_size
    right_border  = get_border(image, swapX=True,  swap=False) + border_size

    top_border    = get_border(image, swapY=False, swap=True) - border_size
    bottom_border = get_border(image, swapY=True,  swap=True) + border_size

    # (0, 0) в левом верхнем углу
    new_x_size = right_border - left_border
    new_y_size = bottom_border - top_border

    new_x_offset = (right_border  - new_x_size)
    new_y_offset = (bottom_border - new_y_size)

    with open(file, "r", encoding="UTF-8") as f:
        content = f.read()
        match = next(re.finditer(r'viewBox="(\d+) (\d+) \d+ \d+"', content))
        old_x_offset = int(match.group(1))
        old_y_offset = int(match.group(2))

    with open(os.path.join("clean", new_name + ".svg"), "w", encoding="UTF-8") as f:
        f.write(re.sub(r'viewBox="\d+ \d+ \d+ \d+"',
                     f'viewBox="{old_x_offset + new_x_offset} {old_y_offset + new_y_offset} {new_x_size} {new_y_size}"',
                     content))