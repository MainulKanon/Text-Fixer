"""Renders the Bangla Facebook post image (1080x1080) from the real Text Fixer widgets.

Run:  .venv\\Scripts\\python marketing\\render_facebook.py
Output: marketing\\facebook\\text-fixer-bn.png
"""
import os
import sys
from pathlib import Path

os.environ["QT_SCALE_FACTOR"] = "2"          # crisp widget captures
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

from config import config  # noqa: E402
from ui.floating_button import FloatingButton  # noqa: E402
from ui.icons import draw_badge  # noqa: E402
from ui.preview_popup import PreviewPopup  # noqa: E402

S = 1080
BG, INK, MUTED, PURPLE, PURPLE_D, GREEN = "#F4F3FB", "#2C2C2A", "#5F5E5A", "#534AB7", "#26215C", "#0F6E56"
BN, EN = "Nirmala UI", "Segoe UI"
MESSY = "hi sir, i has complete the logo design yesterday pls check"
FIXED = "Hi, I completed the logo design yesterday. Please check it."


def font(px, bold=False, family=BN):
    f = QFont(family, 1)
    f.setPixelSize(int(px))
    f.setWeight(QFont.Bold if bold else QFont.Normal)
    return f


def text(p, rect, s, px, color=INK, bold=False, align=Qt.AlignLeft | Qt.AlignTop, family=BN):
    p.setFont(font(px, bold, family))
    p.setPen(QColor(color))
    p.drawText(QRectF(*rect), int(align) | int(Qt.TextWordWrap), s)


def grab(widget):
    pm = widget.grab()
    pm.setDevicePixelRatio(1)
    return pm


# real widgets
btn = grab(FloatingButton())
pv = PreviewPopup(config.mode_names)
pv.show_for({"original": MESSY, "fixed": FIXED, "label": "Groq", "mode": "Fix grammar", "hwnd": 0}, None)
card = grab(pv)
pv.hide()

pm = QPixmap(S, S)
pm.fill(QColor(BG))
p = QPainter(pm)
p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)

# brand
draw_badge(p, QRectF(60, 52, 62, 62))
text(p, (138, 56, 500, 56), "Text Fixer", 38, PURPLE_D, True, Qt.AlignVCenter | Qt.AlignLeft, EN)
p.setPen(QPen(QColor("#AFA9EC"), 2))
p.setBrush(QColor("#EEEDFE"))
p.drawRoundedRect(QRectF(S - 60 - 230, 62, 230, 46), 23, 23)
text(p, (S - 60 - 230, 62, 230, 46), "সম্পূর্ণ ফ্রি", 24, PURPLE_D, True, Qt.AlignCenter)

# headline
text(p, (60, 150, 960, 100), "এক ক্লিকে ইংরেজি ঠিক করুন", 60, PURPLE_D, True)
text(p, (60, 252, 960, 50), "Fiverr, Gmail, WhatsApp, যেকোনো অ্যাপে", 34, MUTED)

# chat box + button + preview card
box = (60, 400, 960, 84)
p.setPen(QPen(QColor("#B4B2A9"), 2))
p.setBrush(QColor("white"))
p.drawRoundedRect(QRectF(*box), 16, 16)
text(p, (box[0] + 26, box[1], box[2] - 52, box[3]), MESSY, 28, INK, align=Qt.AlignVCenter | Qt.AlignLeft, family=EN)
p.drawPixmap(int(box[0] + box[2] - btn.width()), int(box[1] - btn.height() - 12), btn)
scale = min(1.0, 960 / card.width())
c = card.scaledToWidth(int(card.width() * scale), Qt.SmoothTransformation)
p.drawPixmap(int(box[0] + box[2] - c.width()), box[1] + box[3] + 18, c)
y_after = box[1] + box[3] + 18 + c.height()

# benefits
ticks = ["প্রিভিউ দেখে Replace", "বাংলা → ইংরেজি", "রিপ্লাই লিখে দেয়"]
y = y_after + 40
for i, t in enumerate(ticks):
    x = 60 + i * 330
    text(p, (x, y, 40, 44), "✓", 32, GREEN, True, family=EN)
    text(p, (x + 40, y + 2, 290, 44), t, 27, INK, True)

# footer: platforms + website
p.setPen(Qt.NoPen)
p.setBrush(QColor(PURPLE))
p.drawRoundedRect(QRectF(60, S - 150, 960, 90), 22, 22)
text(p, (90, S - 150, 420, 90), "Windows ও Android", 30, "white", True, Qt.AlignVCenter | Qt.AlignLeft)
text(p, (440, S - 150, 560, 90), "mainulkanon.github.io/Text-Fixer", 28, "white", True,
     Qt.AlignVCenter | Qt.AlignRight, EN)
p.end()

out = ROOT / "marketing" / "facebook"
out.mkdir(parents=True, exist_ok=True)
pm.save(str(out / "text-fixer-bn.png"))
print("saved", out / "text-fixer-bn.png")
