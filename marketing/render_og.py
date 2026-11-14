"""Renders docs/og.png (1200x630), the image shown when the website link is shared.

Run: .venv\\Scripts\\python marketing\\render_og.py
"""
import os
import sys
from pathlib import Path

os.environ["QT_SCALE_FACTOR"] = "2"
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])
from ui.floating_button import FloatingButton  # noqa: E402
from ui.icons import draw_badge  # noqa: E402

W, H = 1200, 630
pm = QPixmap(W, H)
pm.fill(QColor("#F6F5FC"))
p = QPainter(pm)
p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)


def font(px, bold=False):
    f = QFont("Segoe UI", 1)
    f.setPixelSize(px)
    f.setWeight(QFont.Bold if bold else QFont.Normal)
    return f


def text(rect, s, px, color, bold=False, align=Qt.AlignLeft | Qt.AlignTop):
    p.setFont(font(px, bold))
    p.setPen(QColor(color))
    p.drawText(QRectF(*rect), int(align) | int(Qt.TextWordWrap), s)


draw_badge(p, QRectF(70, 70, 76, 76))
text((166, 80, 600, 60), "Text Fixer", 46, "#26215C", True)
text((70, 190, 640, 200), "Fix your English in any app, with one click", 56, "#26215C", True)
text((70, 400, 600, 90), "Free for Windows and Android. Works with free AI.", 28, "#5F5E6E")
p.setPen(Qt.NoPen)
p.setBrush(QColor("#534AB7"))
p.drawRoundedRect(QRectF(70, 500, 300, 64), 16, 16)
text((70, 500, 300, 64), "Download free", 26, "white", True, Qt.AlignCenter)

# demo card on the right
p.setPen(QPen(QColor("#E3E1EE"), 2))
p.setBrush(QColor("white"))
p.drawRoundedRect(QRectF(740, 120, 400, 400), 24, 24)
p.setPen(QPen(QColor("#E3E1EE"), 2))
p.setBrush(QColor("white"))
p.drawRoundedRect(QRectF(770, 260, 340, 64), 12, 12)
text((790, 260, 310, 64), "hi sir, i has complete the logo", 20, "#1F1D2B", align=Qt.AlignVCenter)
btn = FloatingButton().grab()
btn.setDevicePixelRatio(1)
btn = btn.scaledToHeight(48, Qt.SmoothTransformation)
p.drawPixmap(int(1110 - btn.width()), 200, btn)
p.setPen(Qt.NoPen)
p.setBrush(QColor("#D7F2E5"))
p.drawRoundedRect(QRectF(770, 350, 340, 120), 12, 12)
text((790, 360, 310, 100), "Hi sir, I completed the logo yesterday. Please check it.", 22, "#085041", True)
p.end()

out = ROOT / "docs" / "og.png"
pm.save(str(out))
print("saved", out)
