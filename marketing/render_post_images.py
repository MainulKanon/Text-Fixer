"""Renders LinkedIn post images (1080x1080) from the real FixIt widgets.

Run:  .venv\\Scripts\\python marketing\\render_post_images.py
Output: marketing\\linkedin\\*.png   (API keys are masked)
"""
import os
import sys
from pathlib import Path

os.environ["QT_SCALE_FACTOR"] = "2"          # crisp, high-res widget captures
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

app = QApplication([])

from config import config  # noqa: E402
from ui.floating_button import FloatingButton  # noqa: E402
from ui.icons import draw_badge  # noqa: E402
from ui.preview_popup import PreviewPopup  # noqa: E402
from ui.reply_window import ReplyWindow  # noqa: E402
from ui.settings import SettingsDialog  # noqa: E402

OUT = ROOT / "marketing" / "linkedin"
OUT.mkdir(parents=True, exist_ok=True)
S = 1080
PURPLE, PURPLE_D, INK, MUTED, BG = "#534AB7", "#26215C", "#2C2C2A", "#5F5E5A", "#F4F3FB"

BAD = "hi sir, i has complete the logo design yesterday , pls check and tell me if any change need"
GOOD = "Hi, I completed the logo design yesterday. Please check it and let me know if any changes are needed."


def px(pm: QPixmap) -> QPixmap:
    pm.setDevicePixelRatio(1)
    return pm


def font(size, bold=False):
    f = QFont("Segoe UI", 1)
    f.setPixelSize(size)
    f.setWeight(QFont.Bold if bold else QFont.Normal)
    return f


def canvas():
    pm = QPixmap(S, S)
    pm.fill(QColor(BG))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    return pm, p


def text(p, rect, s, size, color=INK, bold=False, align=Qt.AlignLeft | Qt.AlignTop):
    p.setFont(font(size, bold))
    p.setPen(QColor(color))
    p.drawText(QRectF(*rect), align | Qt.TextWordWrap, s)


def brand_footer(p, page):
    draw_badge(p, QRectF(60, S - 110, 50, 50))
    text(p, (124, S - 106, 400, 40), "FixIt", 30, PURPLE_D, True)
    text(p, (124, S - 70, 600, 30), "Fix your English in any app, with free AI", 20, MUTED)
    text(p, (S - 160, S - 96, 100, 40), page, 22, MUTED, align=Qt.AlignRight | Qt.AlignTop)


def chat_box(p, x, y, w, h, s, caret=True):
    p.setPen(QPen(QColor("#B4B2A9"), 2))
    p.setBrush(QColor("white"))
    p.drawRoundedRect(QRectF(x, y, w, h), 16, 16)
    text(p, (x + 24, y + 18, w - 48, h - 30), s + (" |" if caret else ""), 26, INK)


def card(p, x, y, w, h, fill="white", border="#D3D1C7"):
    p.setPen(QPen(QColor(border), 2))
    p.setBrush(QColor(fill))
    p.drawRoundedRect(QRectF(x, y, w, h), 24, 24)


def save(pm, p, name):
    p.end()
    pm.save(str(OUT / name))
    print("saved", OUT / name)


# ---------- captures ----------
btn = FloatingButton()
btn_ready = px(btn.grab())

preview = PreviewPopup(config.mode_names)
preview.show_for({"original": BAD + " 😊", "fixed": GOOD + " 😊", "label": "Groq", "mode": "Fix grammar",
                  "hwnd": 0}, None)
preview_pm = px(preview.grab())
preview.hide()

reply = ReplyWindow()
reply.resize(560, 560)
reply.message.setPlainText("Hi, I liked your portfolio. Can you make a logo for my bakery? "
                           "What is your price and how long will it take?")
reply.notes.setText("$40, 3 days")
reply.reply.setPlainText(
    "Thank you for reaching out and for your kind words about my portfolio. I'd be happy to create a logo "
    "for your bakery. The cost is $40, and I can deliver the final files within 3 days. If you'd like to "
    "proceed, please share any ideas or preferences you have for the design, and we can get started right away.")
reply.insert_btn.setEnabled(True)
reply._set_status("Done via Groq. Edit if needed, then Copy or Insert.", True)
reply_pm = px(reply.grab())

settings = SettingsDialog()
for e in settings.key_edits.values():          # never show real keys
    e.setText("x" * 40 if e.text() else "")
settings.model_edits["openrouter"].setEditText("openai/gpt-oss-120b:free")
settings.resize(640, 600)
settings_pm = px(settings.grab())

# ---------- 1. problem → solution ----------
pm, p = canvas()
text(p, (60, 60, 960, 140), "I was tired of copy-pasting my messages into ChatGPT just to fix my English.", 48,
     PURPLE_D, True)
card(p, 60, 260, 470, 640, "#FFFFFF")
text(p, (100, 295, 400, 40), "Before", 30, "#A32D2D", True)
steps = ["Select my message", "Copy it", "Open ChatGPT and paste", "Wait, then copy the answer",
         "Go back and paste it", "Repeat 30 times a day"]
for i, s in enumerate(steps):
    y = 370 + i * 84
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#FCEBEB"))
    p.drawEllipse(QRectF(100, y, 44, 44))
    text(p, (100, y + 4, 44, 40), str(i + 1), 22, "#A32D2D", True, Qt.AlignHCenter | Qt.AlignTop)
    text(p, (160, y + 6, 340, 40), s, 24, INK)
card(p, 550, 260, 470, 640, "#EEEDFE", "#AFA9EC")
text(p, (590, 295, 400, 40), "Now", 30, PURPLE, True)
chat_box(p, 590, 370, 390, 130, "hi sir, i has complete the logo yesterday", caret=False)
p.drawPixmap(int(985 - btn_ready.width()), 520, btn_ready)
text(p, (590, 640, 400, 120), "1 click", 96, PURPLE_D, True)
text(p, (590, 770, 400, 100), "Type anywhere. Click Fix grammar. Done.", 26, MUTED)
brand_footer(p, "1 / 4")
save(pm, p, "1-problem-solution.png")

# ---------- 2. preview ----------
pm, p = canvas()
text(p, (60, 60, 960, 80), "Preview first. Then replace.", 56, PURPLE_D, True)
text(p, (60, 150, 960, 80), "Works in Fiverr, Gmail, WhatsApp Web, Slack, Notepad and any other Windows app.",
     26, MUTED)
chat_box(p, 60, 300, 960 - btn_ready.width() - 20, 76, "hi sir, i has complete the logo design yesterday…",
         caret=False)
p.drawPixmap(int(1020 - btn_ready.width()), int(338 - btn_ready.height() / 2), btn_ready)
scale = min(960 / preview_pm.width(), 1.0)
pv = preview_pm.scaledToWidth(int(preview_pm.width() * scale), Qt.SmoothTransformation)
p.drawPixmap(int(1020 - pv.width()), 400, pv)
y = 400 + pv.height() + 40
for i, s in enumerate(["Green = what changed", "Try again or change style: friendlier, shorter, professional",
                       "Ctrl+Z always brings your original back"]):
    text(p, (60, y + i * 46, 960, 44), "✓  " + s, 26, INK)
brand_footer(p, "2 / 4")
save(pm, p, "2-preview.png")

# ---------- 3. reply assistant ----------
pm, p = canvas()
text(p, (60, 60, 960, 130), "It writes replies too.", 56, PURPLE_D, True)
text(p, (60, 145, 960, 80), "Select a client's message, press Ctrl+Shift+R, add a short note. Get a ready reply.",
     26, MUTED)
avail_w, avail_h = 960, S - 260 - 140
r = reply_pm.scaled(avail_w, avail_h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
p.setPen(QPen(QColor("#D3D1C7"), 2))
p.setBrush(Qt.NoBrush)
x0 = int((S - r.width()) / 2)
p.drawPixmap(x0, 250, r)
p.drawRoundedRect(QRectF(x0, 250, r.width(), r.height()), 8, 8)
brand_footer(p, "3 / 4")
save(pm, p, "3-reply.png")

# ---------- 4. free AI ----------
pm, p = canvas()
text(p, (60, 60, 960, 80), "Free AI. Your keys stay on your PC.", 56, PURPLE_D, True)
text(p, (60, 150, 960, 80), "Groq (about 1 second), Gemini and OpenRouter. If one hits its limit, FixIt uses the next.",
     26, MUTED)
st = settings_pm.scaled(960, S - 270 - 140, Qt.KeepAspectRatio, Qt.SmoothTransformation)
x0 = int((S - st.width()) / 2)
p.drawPixmap(x0, 270, st)
brand_footer(p, "4 / 4")
save(pm, p, "4-free-ai.png")

# raw captures too
for name, pmx in (("raw-preview.png", preview_pm), ("raw-reply.png", reply_pm), ("raw-button.png", btn_ready)):
    pmx.save(str(OUT / name))
