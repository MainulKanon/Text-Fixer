"""Renders the FixIt promo video (English or Bangla) from the real FixIt widgets.

Usage:
  .venv\\Scripts\\python marketing\\video\\make_video.py en            # 1920x1080
  .venv\\Scripts\\python marketing\\video\\make_video.py bn --square   # 1080x1080 LinkedIn feed cut
  ... --preview   (every 3rd frame at 10 fps, fast check, no audio)

If marketing\\video\\audio\\<lang>\\1.mp3 … 8.mp3 exist, each scene lasts as long as its voice clip
(plus a little breathing room) and the voice is mixed in. Otherwise, default timings are used (silent).
Output: marketing\\video\\out\\FixIt-<lang>[-square].mp4
"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

os.environ["QT_SCALE_FACTOR"] = "3"    # large, crisp widget captures (readable in 1080p)
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT))

import imageio_ffmpeg  # noqa: E402
from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: E402
from PySide6.QtGui import (QColor, QFont, QFontMetricsF, QImage, QPainter, QPainterPath, QPen,  # noqa: E402
                           QPixmap, QPolygonF)
from PySide6.QtWidgets import QApplication  # noqa: E402

app = QApplication([])

from config import config  # noqa: E402
from ui.floating_button import FloatingButton  # noqa: E402
from ui.icons import draw_badge  # noqa: E402
from ui.preview_popup import PreviewPopup  # noqa: E402
from ui.reply_window import ReplyWindow  # noqa: E402

FF = imageio_ffmpeg.get_ffmpeg_exe()
FPS = 30
W, H = 1920, 1080
BG, INK, MUTED, PURPLE, PURPLE_D = "#F4F3FB", "#2C2C2A", "#5F5E5A", "#534AB7", "#26215C"
GREEN, RED = "#0F6E56", "#A32D2D"
DEFAULT_DURS = [6, 13, 6, 16, 10, 12, 8, 7]
LEAD, TAIL = 0.25, 0.55        # silence before / after each voice clip

VO = json.loads((HERE / "voiceover.json").read_text(encoding="utf-8"))

TEXT = {
    "en": {
        "chat_title": "Client", "client_msg": "Hi! Any update on my logo?",
        "messy": "hi sir, i has complete the logo yesterday pls check",
        "fixed": "Hi, I completed the logo yesterday. Please check it.",
        "g_ok": "Fixes grammar", "g_no": "Doesn't make it natural and professional",
        "steps": ["Copy", "Open ChatGPT", "Paste", "Copy answer", "Paste back"],
        "per_day": "× {n} a day", "tagline": "AI in every text box",
        "apps": "Fiverr  ·  Gmail  ·  WhatsApp  ·  Slack  ·  any app",
        "msg_label": "Message to client",
        "bangla": "Write in Bangla, get English",
        "reply_label": "Client's message", "reply_msg": "Hi, I liked your portfolio. Can you make a logo for my bakery? What is your price and how long will it take?",
        "free_ai": "Free AI", "one_sec": "≈ 1 second", "keys": "Keys stay on your PC",
        "built": "Built with AI", "cta": "Comment “FixIt” 👇",
    },
    "bn": {
        "chat_title": "ক্লায়েন্ট", "client_msg": "Hi! Any update on my logo?",
        "messy": "hi sir, i has complete the logo yesterday pls check",
        "fixed": "Hi, I completed the logo yesterday. Please check it.",
        "g_ok": "গ্রামার ঠিক করে", "g_no": "স্বাভাবিক আর প্রফেশনাল করে না",
        "steps": ["কপি", "ChatGPT খোলা", "পেস্ট", "উত্তর কপি", "আবার পেস্ট"],
        "per_day": "× দিনে {n} বার", "tagline": "প্রতিটা টেক্সট বক্সে AI",
        "apps": "Fiverr  ·  Gmail  ·  WhatsApp  ·  Slack  ·  যেকোনো অ্যাপ",
        "msg_label": "ক্লায়েন্টকে মেসেজ",
        "bangla": "বাংলায় লিখুন, ইংরেজি পান",
        "reply_label": "ক্লায়েন্টের মেসেজ", "reply_msg": "Hi, I liked your portfolio. Can you make a logo for my bakery? What is your price and how long will it take?",
        "free_ai": "ফ্রি AI", "one_sec": "≈ ১ সেকেন্ড", "keys": "Key থাকে আপনার পিসিতেই",
        "built": "AI দিয়ে তৈরি", "cta": "কমেন্টে “FixIt” লিখুন 👇",
    },
}

FRIENDLY = "Hi! I finished the logo yesterday. Have a look and let me know what you think!"
BANGLA_IN = "ami kal kaj ta shesh kore pathabo"
BANGLA_OUT = "I will finish the work tomorrow and send it."


# ---------------------------------------------------------------- helpers
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):                      # ease-out cubic
    x = clamp(x)
    return 1 - (1 - x) ** 3


def ease_back(x):                 # ease-out with a small overshoot
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


def span(t, a, b):
    """0 → 1 progress of t between a and b (seconds)."""
    return clamp((t - a) / max(1e-6, b - a))


def lerp(a, b, x):
    return a + (b - a) * x


def px(pm: QPixmap) -> QPixmap:
    pm.setDevicePixelRatio(1)
    return pm


class Ctx:
    def __init__(self, lang: str) -> None:
        self.lang = lang
        self.T = TEXT[lang]
        self.family = "Nirmala UI" if lang == "bn" else "Segoe UI"

    def font(self, size, bold=False, latin=False):
        f = QFont("Segoe UI" if latin else self.family, 1)
        f.setPixelSize(int(size))
        f.setWeight(QFont.Bold if bold else QFont.Normal)
        return f


def text(p, ctx, rect, s, size, color=INK, bold=False, align=Qt.AlignLeft | Qt.AlignTop, alpha=1.0, latin=False):
    p.save()
    p.setOpacity(p.opacity() * alpha)
    p.setFont(ctx.font(size, bold, latin))
    p.setPen(QColor(color))
    p.drawText(QRectF(*rect), int(align) | int(Qt.TextWordWrap), s)
    p.restore()


def rrect(p, rect, radius, fill, border=None, width=2):
    p.setPen(QPen(QColor(border), width) if border else Qt.NoPen)
    p.setBrush(QColor(fill) if fill else Qt.NoBrush)
    p.drawRoundedRect(QRectF(*rect), radius, radius)


def pixmap(p, pm, x, y, alpha=1.0, scale=1.0):
    p.save()
    p.setOpacity(p.opacity() * alpha)
    if scale != 1.0:
        p.translate(x + pm.width() / 2, y + pm.height() / 2)
        p.scale(scale, scale)
        p.drawPixmap(int(-pm.width() / 2), int(-pm.height() / 2), pm)
    else:
        p.drawPixmap(int(x), int(y), pm)
    p.restore()


def cursor(p, x, y, pressed=False):
    poly = QPolygonF([QPointF(0, 0), QPointF(0, 34), QPointF(9, 26), QPointF(15, 40), QPointF(21, 37),
                      QPointF(15, 24), QPointF(26, 24)])
    p.save()
    p.translate(x, y)
    if pressed:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(83, 74, 183, 70))
        p.drawEllipse(QPointF(0, 0), 26, 26)
    p.setPen(QPen(QColor("white"), 2.5))
    p.setBrush(QColor("#1b1b1b"))
    p.drawPolygon(poly)
    p.restore()


def keycap(p, ctx, x, y, label, alpha):
    fm = QFontMetricsF(ctx.font(34, True, latin=True))
    w = fm.horizontalAdvance(label) + 48
    p.save()
    p.setOpacity(alpha)
    rrect(p, (x, y + 6, w, 76), 14, "#B4B2A9")
    rrect(p, (x, y, w, 76), 14, "white", "#B4B2A9")
    text(p, ctx, (x, y, w, 76), label, 34, INK, True, Qt.AlignCenter, latin=True)
    p.restore()
    return w


def typed(s, x):
    n = int(round(len(s) * clamp(x)))
    return s[:n]


def caret_on(t):
    return (t * 2) % 2 < 1.2


# ---------------------------------------------------------------- assets (real widgets)
class Assets:
    def __init__(self) -> None:
        b = FloatingButton()
        self.btn = px(b.grab())
        b.set_busy(True)
        b._angle = 60
        self.btn_busy = px(b.grab())
        b.set_busy(False)
        b.show_done()
        self.btn_done = px(b.grab())

        pv = PreviewPopup(config.mode_names)
        base = {"label": "Groq", "hwnd": 0}
        pv.show_for({**base, "original": TEXT["en"]["messy"], "fixed": TEXT["en"]["fixed"], "mode": "Fix grammar"}, None)
        self.preview = px(pv.grab())
        pv.show_for({**base, "original": TEXT["en"]["messy"], "fixed": FRIENDLY, "mode": "Friendlier"}, None)
        self.preview_friendly = px(pv.grab())
        pv.hide()


REPLY_TEXT = ("Thank you for reaching out and for your kind words about my portfolio. I'd be happy to create a "
              "logo for your bakery. The cost is $40, and I can deliver the final files within 3 days. Please "
              "share any ideas you have, and we can get started right away.")


# ---------------------------------------------------------------- scenes
# Each scene: f(p, ctx, A, t, d)  t = seconds into the scene, d = scene duration. Content stays above y=900.

def chat_input(p, ctx, rect, s, show_caret, t, alpha=1.0):
    x, y, w, h = rect
    p.save()
    p.setOpacity(alpha)
    rrect(p, rect, 18, "white", "#B4B2A9", 2)
    text(p, ctx, (x + 28, y, w - 56, h), s + ("|" if show_caret and caret_on(t) else ""), 34, INK,
         align=Qt.AlignVCenter | Qt.AlignLeft, latin=True)
    p.restore()


def s1_hook(p, ctx, A, t, d):
    T = ctx.T
    a = ease(span(t, 0, 0.6))
    p.save()
    p.setOpacity(a)
    rrect(p, (360, 110, 1200, 760), 28, "white", "#D3D1C7")
    p.setPen(Qt.NoPen)
    p.setBrush(QColor("#EEEDFE"))
    p.drawEllipse(QRectF(400, 140, 64, 64))
    text(p, ctx, (400, 140, 64, 64), "C", 30, PURPLE, True, Qt.AlignCenter, latin=True)
    text(p, ctx, (484, 152, 600, 44), T["chat_title"], 30, INK, True)
    p.setPen(QPen(QColor("#E5E3DC"), 2))
    p.drawLine(360, 230, 1560, 230)
    rrect(p, (400, 270, 560, 80), 22, "#F1EFE8")
    text(p, ctx, (424, 270, 540, 80), T["client_msg"], 30, INK, align=Qt.AlignVCenter, latin=True)
    p.restore()
    chat_input(p, ctx, (400, 740, 1120, 96), typed(T["messy"], span(t, 0.8, d * 0.75)), True, t, a)


def s2_problem(p, ctx, A, t, d):
    T = ctx.T
    half = d * 0.38
    if t < half + 0.4:                                   # part A: Grammarly
        out = 1 - span(t, half, half + 0.4)
        a = ease(span(t, 0, 0.5)) * out
        rrect(p, (460, 200, 1000, 120), 24, "white", "#D3D1C7") if a else None
        text(p, ctx, (460, 200, 1000, 120), "Grammarly", 56, INK, True, Qt.AlignCenter, alpha=a, latin=True)
        y1 = lerp(420, 380, ease(span(t, 0.6, 1.2)))
        text(p, ctx, (460, y1, 1000, 80), "✓  " + T["g_ok"], 46, GREEN, True, Qt.AlignCenter,
             alpha=ease(span(t, 0.6, 1.2)) * out)
        y2 = lerp(540, 500, ease(span(t, 1.8, 2.4)))
        text(p, ctx, (300, y2, 1320, 80), "✗  " + T["g_no"], 46, RED, True, Qt.AlignCenter,
             alpha=ease(span(t, 1.8, 2.4)) * out)
        return
    tt = t - half                                         # part B: copy-paste loop
    dd = d - half
    steps = T["steps"]
    n = len(steps)
    total_w = 1680
    cw, gap = 290, (total_w - 5 * 290) / 4
    x0 = (W - total_w) / 2
    for i, s in enumerate(steps):
        # Steps light up in a loop that speeds up.
        cycle = 0.45 * max(0.25, 1 - tt / dd)
        k = int(tt / cycle) % n if tt > 0.3 else -1
        a = ease(span(tt, 0.08 * i, 0.08 * i + 0.4))
        on = k == i
        x = x0 + i * (cw + gap)
        rrect(p, (x, 330, cw, 130), 22, "#FCEBEB" if on else "white", RED if on else "#D3D1C7", 3 if on else 2) \
            if a > 0 else None
        text(p, ctx, (x, 330, cw, 130), s, 36, RED if on else INK, True, Qt.AlignCenter, alpha=a)
        if i < n - 1:
            text(p, ctx, (x + cw, 330, gap, 130), "→", 44, MUTED, False, Qt.AlignCenter, alpha=a, latin=True)
    count = int(lerp(1, 30, ease(span(tt, 0.5, dd - 0.6))))
    text(p, ctx, (0, 560, W, 160), T["per_day"].format(n=count if ctx.lang == "en" else to_bn(count)), 110,
         RED, True, Qt.AlignHCenter | Qt.AlignTop, alpha=ease(span(tt, 0.4, 0.9)))


def to_bn(n: int) -> str:
    return str(n).translate(str.maketrans("0123456789", "০১২৩৪৫৬৭৮৯"))


def logo_block(p, ctx, t, cy, sub):
    s = ease_back(span(t, 0, 0.7))
    p.save()
    p.translate(W / 2, cy)
    p.scale(s, s)
    draw_badge(p, QRectF(-110, -110, 220, 220))
    p.restore()
    text(p, ctx, (0, cy + 140, W, 120), "FixIt", 110, PURPLE_D, True, Qt.AlignHCenter, alpha=ease(span(t, 0.3, 0.9)),
         latin=True)
    text(p, ctx, (0, cy + 270, W, 80), sub, 46, MUTED, False, Qt.AlignHCenter, alpha=ease(span(t, 0.6, 1.2)))


def s3_reveal(p, ctx, A, t, d):
    logo_block(p, ctx, t, 300, ctx.T["tagline"])


def s4_demo(p, ctx, A, t, d):
    T = ctx.T
    k = d / 16.0                                         # timings below assume a 16 s scene
    field = (260, 250, 1400, 96)
    text(p, ctx, (260, 120, 1400, 50), T["apps"], 32, PURPLE, True, alpha=ease(span(t, 0, 0.6)))
    text(p, ctx, (260, 190, 800, 44), T["msg_label"], 28, MUTED, alpha=ease(span(t, 0, 0.6)))
    replaced = t > 12.0 * k
    s = T["fixed"] if replaced else T["messy"]
    chat_input(p, ctx, field, s, True, t, ease(span(t, 0, 0.5)))
    fx, fy, fw, fh = field
    # button above the field's top-right corner
    bx, by = fx + fw - A.btn.width(), fy - A.btn.height() - 14
    btn = A.btn
    if 4.2 * k < t < 6.0 * k:
        btn = A.btn_busy
    elif replaced:
        btn = A.btn_done
    show_btn = t > 1.6 * k and (t < 6.0 * k or t > 12.0 * k)
    if show_btn:
        pixmap(p, btn, bx, by + 12 * (1 - ease(span(t, 1.6 * k, 2.1 * k))), ease(span(t, 1.6 * k, 2.1 * k)))
    # preview card below the field
    pv = A.preview
    px_, py_ = fx + fw - pv.width(), fy + fh + 18
    if 6.0 * k <= t <= 12.0 * k:
        a = ease(span(t, 6.0 * k, 6.5 * k)) * (1 - span(t, 11.7 * k, 12.0 * k))
        pixmap(p, pv, px_, py_ + 20 * (1 - a), a)
    # mouse
    start, to_btn, to_rep = (1500, 820), (bx + btn.width() * 0.4, by + btn.height() * 0.6), \
        (px_ + 90, py_ + pv.height() - 60)
    if t < 6.0 * k:
        m = ease(span(t, 2.4 * k, 3.8 * k))
        x, y = lerp(start[0], to_btn[0], m), lerp(start[1], to_btn[1], m)
        pressed = 3.9 * k < t < 4.4 * k
    else:
        m = ease(span(t, 9.0 * k, 10.8 * k))
        x, y = lerp(to_btn[0], to_rep[0], m), lerp(to_btn[1], to_rep[1], m)
        pressed = 11.0 * k < t < 11.6 * k
    if t > 2.2 * k:
        cursor(p, x, y, pressed)
    if t > 13.0 * k:
        text(p, ctx, (260, 420, 1400, 60), "Ctrl+Z  →  original", 34, MUTED, True, alpha=ease(span(t, 13.0 * k, 13.6 * k)),
             latin=True)


def s5_styles(p, ctx, A, t, d):
    T = ctx.T
    half = d * 0.55
    if t < half + 0.4:
        out = 1 - span(t, half, half + 0.4)
        pv = A.preview_friendly if t > 2.4 else A.preview
        cx, cy = (W - pv.width()) / 2, 170
        pixmap(p, A.preview, cx, cy, ease(span(t, 0, 0.4)) * out * (1 - span(t, 2.2, 2.6)))
        if t > 2.2:
            pixmap(p, A.preview_friendly, cx, cy, span(t, 2.2, 2.6) * out)
        # style menu dropping from "Change style"
        ma = ease(span(t, 0.6, 1.0)) * (1 - span(t, 2.3, 2.6)) * out
        if ma > 0:
            mx, my = cx + pv.width() - 600, cy + 120
            p.save()
            p.setOpacity(ma)
            rrect(p, (mx, my, 540, 360), 18, "white", "#D3D1C7")
            for i, name in enumerate(["More professional", "Shorter", "Friendlier", "Bangla → English"]):
                hl = name == "Friendlier" and t > 1.5
                if hl:
                    rrect(p, (mx + 10, my + 12 + i * 84, 520, 76), 12, "#EEEDFE")
                text(p, ctx, (mx + 34, my + 12 + i * 84, 480, 76), name, 36, PURPLE_D if hl else INK, hl,
                     Qt.AlignVCenter, latin=True)
            p.restore()
            cursor(p, mx + 260, lerp(my + 50, my + 12 + 2 * 84 + 38, ease(span(t, 1.0, 1.5))), 1.6 < t < 2.0)
        return
    tt = t - half
    a = ease(span(tt, 0, 0.5))
    text(p, ctx, (0, 170, W, 80), T["bangla"], 54, PURPLE_D, True, Qt.AlignHCenter, alpha=a)
    rrect(p, (260, 330, 1400, 110), 20, "white", "#D3D1C7") if a else None
    text(p, ctx, (300, 330, 1340, 110), BANGLA_IN, 40, INK, align=Qt.AlignVCenter, alpha=a, latin=True)
    text(p, ctx, (0, 455, W, 80), "↓", 60, PURPLE, True, Qt.AlignHCenter, alpha=ease(span(tt, 0.6, 1.0)), latin=True)
    b = ease(span(tt, 1.0, 1.4))
    rrect(p, (260, 560, 1400, 110), 20, "#E1F5EE", "#5DCAA5") if b else None
    text(p, ctx, (300, 560, 1340, 110), typed(BANGLA_OUT, span(tt, 1.2, 2.6)), 40, "#085041", True,
         Qt.AlignVCenter, alpha=b, latin=True)


def s6_reply(p, ctx, A, t, d):
    T = ctx.T
    k = d / 12.0
    if t < 4.2 * k:
        out = 1 - span(t, 3.8 * k, 4.2 * k)
        a = ease(span(t, 0, 0.4)) * out
        text(p, ctx, (260, 150, 1400, 50), T["reply_label"], 30, MUTED, alpha=a)
        box = (260, 210, 1400, 200)
        rrect(p, box, 24, "#F1EFE8") if a else None
        # selection sweep
        sel = ease(span(t, 0.5 * k, 1.6 * k))
        if sel > 0:
            p.save()
            p.setOpacity(out)
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(55, 138, 221, 70))
            p.drawRoundedRect(QRectF(280, 230, 1360 * sel, 160), 10, 10)
            p.restore()
        text(p, ctx, (300, 230, 1320, 160), T["reply_msg"], 36, INK, align=Qt.AlignVCenter, alpha=a, latin=True)
        ka = ease_back(span(t, 1.9 * k, 2.4 * k)) * out
        if ka > 0:
            x = 610
            for i, lab in enumerate(["Ctrl", "+", "Shift", "+", "R"]):
                if lab == "+":
                    text(p, ctx, (x, 520, 60, 76), "+", 40, MUTED, True, Qt.AlignCenter, alpha=ka, latin=True)
                    x += 60
                else:
                    x += keycap(p, ctx, x, 520, lab, clamp(ka)) + 6
        return
    # Reply assistant card (drawn large so it reads well on a phone)
    tt = t - 4.2 * k
    dd = d - 4.2 * k
    a = ease(span(tt, 0, 0.5))
    x, y = 260, 90 + 30 * (1 - a)
    p.save()
    p.setOpacity(a)
    rrect(p, (x, y, 1400, 820), 28, "white", "#D3D1C7")
    draw_badge(p, QRectF(x + 40, y + 34, 54, 54))
    text(p, ctx, (x + 110, y + 34, 800, 54), "Reply assistant", 36, PURPLE_D, True, Qt.AlignVCenter, latin=True)
    rrect(p, (x + 40, y + 115, 1320, 120), 16, "#F1EFE8")
    text(p, ctx, (x + 64, y + 115, 1280, 120), T["reply_msg"], 30, INK, align=Qt.AlignVCenter, latin=True)
    rrect(p, (x + 40, y + 260, 520, 76), 14, "white", "#B4B2A9")
    text(p, ctx, (x + 64, y + 260, 480, 76), typed("$40, 3 days", span(tt, 0.6, 1.6)) +
         ("|" if tt < 1.9 and caret_on(tt) else ""), 32, INK, align=Qt.AlignVCenter, latin=True)
    rrect(p, (x + 580, y + 260, 260, 76), 38, "#EEEDFE", "#AFA9EC")
    text(p, ctx, (x + 580, y + 260, 260, 76), "Professional", 28, PURPLE_D, True, Qt.AlignCenter, latin=True)
    pulse = 1 + 0.06 * math.sin(span(tt, 1.7, 2.3) * math.pi)
    p.save()
    p.translate(x + 1210, y + 298)
    p.scale(pulse, pulse)
    rrect(p, (-150, -38, 300, 76), 14, PURPLE)
    text(p, ctx, (-150, -38, 300, 76), "✨ Generate", 30, "white", True, Qt.AlignCenter, latin=True)
    p.restore()
    rrect(p, (x + 40, y + 370, 1320, 410), 16, "#FAFAF7", "#E5E3DC")
    text(p, ctx, (x + 70, y + 395, 1260, 370), typed(REPLY_TEXT, span(tt, 2.3, max(2.4, dd - 1.0))), 33, INK,
         latin=True)
    p.restore()


def chip(p, ctx, cx, y, label, a, fill="white", color=INK):
    fm = QFontMetricsF(ctx.font(44, True))
    w = fm.horizontalAdvance(label) + 80
    s = ease_back(a)
    p.save()
    p.setOpacity(clamp(a))
    p.translate(cx, y + 50)
    p.scale(s, s)
    rrect(p, (-w / 2, -50, w, 100), 50, fill, "#AFA9EC", 2)
    text(p, ctx, (-w / 2, -50, w, 100), label, 44, color, True, Qt.AlignCenter)
    p.restore()


def lock_icon(p, cx, cy, a):
    p.save()
    p.setOpacity(a)
    p.setPen(QPen(QColor(PURPLE), 10, c=Qt.RoundCap) if False else QPen(QColor(PURPLE), 10))
    p.setBrush(Qt.NoBrush)
    p.drawArc(QRectF(cx - 34, cy - 70, 68, 80), 0, 180 * 16)
    p.drawLine(QPointF(cx - 34, cy - 30), QPointF(cx - 34, cy - 10))
    p.drawLine(QPointF(cx + 34, cy - 30), QPointF(cx + 34, cy - 10))
    rrect(p, (cx - 56, cy - 14, 112, 92), 14, PURPLE)
    p.restore()


def s7_free(p, ctx, A, t, d):
    T = ctx.T
    text(p, ctx, (0, 110, W, 90), T["free_ai"], 64, PURPLE_D, True, Qt.AlignHCenter, alpha=ease(span(t, 0, 0.5)))
    for i, name in enumerate(["Groq", "Gemini", "OpenRouter"]):
        chip(p, ctx, 560 + i * 400, 250, name, span(t, 0.3 + 0.25 * i, 0.8 + 0.25 * i))
    sec = lerp(0, 0.9, ease(span(t, 1.6, 2.6)))
    text(p, ctx, (0, 420, W, 120), f"{sec:.1f}s", 100, GREEN, True, Qt.AlignHCenter, alpha=ease(span(t, 1.5, 1.9)),
         latin=True)
    text(p, ctx, (0, 540, W, 60), T["one_sec"], 38, MUTED, False, Qt.AlignHCenter, alpha=ease(span(t, 2.4, 2.8)))
    la = ease(span(t, d * 0.55, d * 0.55 + 0.5))
    lock_icon(p, W / 2 - 330, 740, la)
    text(p, ctx, (W / 2 - 250, 690, 900, 90), T["keys"], 48, INK, True, Qt.AlignVCenter, alpha=la)


def s8_outro(p, ctx, A, t, d):
    logo_block(p, ctx, t, 230, ctx.T["built"])
    a = ease_back(span(t, 1.2, 1.8))
    if a > 0:
        fm = QFontMetricsF(ctx.font(48, True))
        w = fm.horizontalAdvance(ctx.T["cta"]) + 120
        p.save()
        p.setOpacity(clamp(a))
        p.translate(W / 2, 700)
        p.scale(a, a)
        rrect(p, (-w / 2, -55, w, 110), 55, PURPLE)
        text(p, ctx, (-w / 2, -55, w, 110), ctx.T["cta"], 48, "white", True, Qt.AlignCenter)
        p.restore()


SCENES = [s1_hook, s2_problem, s3_reveal, s4_demo, s5_styles, s6_reply, s7_free, s8_outro]


# ---------------------------------------------------------------- captions
def caption_chunks(s: str, lang: str) -> list[str]:
    parts = re.split(r"(?<=[.!?।:])\s+", s.strip())
    out = []
    for part in parts:                                    # split long sentences at commas
        if len(part) > 70 and "," in part:
            bits = [b.strip() for b in part.split(",")]
            cur = ""
            for b in bits:
                if cur and len(cur) + len(b) > 60:
                    out.append(cur + ",")
                    cur = b
                else:
                    cur = f"{cur}, {b}" if cur else b
            if cur:
                out.append(cur)
        else:
            out.append(part)
    return [o for o in out if o]


def draw_caption(p, ctx, scene_i, t, d, voice_d, top, width, height):
    chunks = caption_chunks(VO[ctx.lang][scene_i], ctx.lang)
    total = sum(len(c) for c in chunks)
    tv = t - LEAD
    if tv < 0 or tv > voice_d + 0.2:
        return
    acc = 0.0
    for c in chunks:
        dur = voice_d * len(c) / total
        if tv <= acc + dur:
            break
        acc += dur
    fnt = ctx.font(36)
    fm = QFontMetricsF(fnt)
    maxw = width - 240
    br = fm.boundingRect(QRectF(0, 0, maxw, 400), int(Qt.TextWordWrap | Qt.AlignCenter), c)
    bw, bh = br.width() + 56, br.height() + 28
    x, y = (width - bw) / 2, top + (height - bh) / 2
    rrect(p, (x, y, bw, bh), 16, "#CC1F1E2E")
    p.setFont(fnt)
    p.setPen(QColor("white"))
    p.drawText(QRectF(x, y, bw, bh), int(Qt.AlignCenter | Qt.TextWordWrap), c)


# ---------------------------------------------------------------- audio + timing
def clip_duration(path: Path) -> float:
    r = subprocess.run([FF, "-i", str(path)], capture_output=True, text=True, encoding="utf-8", errors="replace")
    m = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", r.stderr)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))


def timing(lang: str):
    adir = HERE / "audio" / lang
    clips = [adir / f"{i}.mp3" for i in range(1, 9)]
    if all(c.exists() for c in clips):
        voice = [clip_duration(c) for c in clips]
        return [max(v + LEAD + TAIL, 3.0) for v in voice], voice, clips
    return [float(x) for x in DEFAULT_DURS], [x - LEAD - TAIL for x in DEFAULT_DURS], None


def build_audio(clips, durs, out: Path) -> None:
    args = [FF, "-y"]
    for c in clips:
        args += ["-i", str(c)]
    filt = []
    for i, d in enumerate(durs):
        filt.append(f"[{i}:a]aresample=44100,adelay={int(LEAD * 1000)}:all=1,apad=whole_dur={d:.3f},"
                    f"atrim=0:{d:.3f}[a{i}]")
    filt.append("".join(f"[a{i}]" for i in range(len(durs))) + f"concat=n={len(durs)}:v=0:a=1[out]")
    args += ["-filter_complex", ";".join(filt), "-map", "[out]", "-c:a", "aac", "-b:a", "192k", str(out)]
    subprocess.run(args, check=True, capture_output=True)


# ---------------------------------------------------------------- render
def render(lang: str, square: bool, preview: bool) -> Path:
    ctx = Ctx(lang)
    A = Assets()
    durs, voice, clips = timing(lang)
    fps = 10 if preview else FPS
    out_dir = HERE / "out"
    out_dir.mkdir(exist_ok=True)
    name = f"FixIt-{lang}{'-square' if square else ''}{'-preview' if preview else ''}.mp4"
    out = out_dir / name
    OW, OH = (1080, 1080) if square else (W, H)

    audio = None
    if clips and not preview:
        audio = out_dir / f"voice-{lang}.m4a"
        build_audio(clips, durs, audio)

    cmd = [FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{OW}x{OH}", "-r", str(fps),
           "-i", "-"]
    if audio:
        cmd += ["-i", str(audio)]
    cmd += ["-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
    if audio:
        cmd += ["-c:a", "copy", "-shortest"]
    cmd += [str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    stage = QImage(W, H, QImage.Format_RGBA8888)
    frame = QImage(OW, OH, QImage.Format_RGBA8888)
    total = sum(durs)
    nframes = int(math.ceil(total * fps))
    starts = [sum(durs[:i]) for i in range(len(durs))]
    for fi in range(nframes):
        tg = fi / fps
        si = max(i for i in range(len(durs)) if starts[i] <= tg + 1e-9)
        t, d = tg - starts[si], durs[si]
        stage.fill(QColor(BG))
        p = QPainter(stage)
        p.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
        fade = min(span(t, 0, 0.25), 1 - span(t, d - 0.2, d)) if si not in (0,) else 1 - span(t, d - 0.2, d)
        p.setOpacity(fade)
        SCENES[si](p, ctx, A, t, d)
        p.setOpacity(1)
        if not square:
            draw_caption(p, ctx, si, t, d, voice[si], 930, W, 150)
            # small brand mark
            draw_badge(p, QRectF(W - 120, 40, 60, 60))
        p.end()

        if square:
            frame.fill(QColor(BG))
            q = QPainter(frame)
            q.setRenderHints(QPainter.Antialiasing | QPainter.TextAntialiasing | QPainter.SmoothPixmapTransform)
            draw_badge(q, QRectF(40, 40, 64, 64))
            q.setFont(ctx.font(40, True, latin=True))
            q.setPen(QColor(PURPLE_D))
            q.drawText(QRectF(122, 40, 600, 64), int(Qt.AlignVCenter), "FixIt")
            q.drawImage(QRectF(0, 200, 1080, 608), stage)
            draw_caption(q, ctx, si, t, d, voice[si], 830, 1080, 230)
            q.end()
            img = frame
        else:
            img = stage
        proc.stdin.write(bytes(img.constBits()))
        if fi % (fps * 10) == 0:
            print(f"  {lang}{' square' if square else ''}: {tg:5.1f}s / {total:.1f}s", flush=True)
    proc.stdin.close()
    proc.wait()
    print("saved", out, f"({total:.1f}s{', with voice' if audio else ', silent'})")
    return out


if __name__ == "__main__":
    lang = sys.argv[1] if len(sys.argv) > 1 else "en"
    render(lang, "--square" in sys.argv, "--preview" in sys.argv)
