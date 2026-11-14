"""The floating "✨ Fix grammar" pill (style B). Never takes focus from the text field."""
from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PySide6.QtWidgets import QWidget

from . import winstyle
from .icons import sparkle_path

HEIGHT = 28          # logical px
PAD_L, PAD_R, ICON, GAP = 9, 12, 14, 6

# state -> (background, border, text/icon color, label)
STATES = {
    "ready": ("#EEEDFE", "#AFA9EC", "#3C3489", "Fix grammar"),
    "hover": ("#CECBF6", "#7F77DD", "#26215C", "Fix grammar"),
    "busy":  ("#EEEDFE", "#AFA9EC", "#534AB7", "Fixing…"),
    "done":  ("#E1F5EE", "#5DCAA5", "#085041", "Fixed · Ctrl+Z to undo"),
}


def compute_position(field, caret, mouse, w, h, work_area) -> tuple[int, int]:
    """Where the pill goes (physical px). It sits ABOVE the text field, right-aligned, so it never
    covers the field's own buttons (send, mic, search…) on the right side."""
    gap = max(6, h // 3)
    if field:
        l, t, r, b = field
        wl, wt, wr, wb = work_area(r, (t + b) // 2)
        tall = (b - t) > 4 * h
        if tall and caret:
            # Multi-line editor (Gmail compose, Notepad): stay next to where you're typing.
            cl, ct, cr, cb = caret
            x, y = cr + gap * 2, (ct + cb) // 2 - h // 2      # after the caret, same line
            if x + w > r:
                x, y = cl, ct - h - gap // 2                   # no room: just above the caret line
        else:
            x, y = r - w, t - h - gap                          # above the top-right corner
            if y < wt:
                y = b + gap                                    # no room above: below the field
    elif caret:
        cl, ct, cr, cb = caret
        x, y = cl, ct - h - gap
        wl, wt, wr, wb = work_area(cl, ct)
    else:
        x, y = mouse[0] + 16, mouse[1] + 16
        wl, wt, wr, wb = work_area(*mouse)
    x = max(wl, min(int(x), wr - w))
    y = max(wt, min(int(y), wb - h))
    return x, y


class FloatingButton(QWidget):
    clicked = Signal()
    right_clicked = Signal(object)   # QPoint (global, logical)
    hover_changed = Signal(bool)
    done_finished = Signal()

    def __init__(self) -> None:
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip("Fix with AI (right-click for more options)")
        self._font = QFont("Segoe UI", 9)
        self._font.setWeight(QFont.DemiBold)
        self._state = "ready"
        self._hover = False
        self._angle = 0
        self._spin = QTimer(self, interval=30, timeout=self._tick)
        self._done_timer = QTimer(self, singleShot=True, timeout=self._done_over)
        self._resize_for("ready")
        self.hwnd = winstyle.make_non_activating(self)
        self.target_hwnd = 0
        self.last_field = None

    # never activate on click
    def nativeEvent(self, event_type, message):
        if winstyle.is_mouse_activate(message):
            return True, winstyle.MA_NOACTIVATE
        return super().nativeEvent(event_type, message)

    # ---------- states ----------
    @property
    def busy(self) -> bool:
        return self._state == "busy"

    def _resize_for(self, state: str) -> None:
        w = PAD_L + ICON + GAP + QFontMetrics(self._font).horizontalAdvance(STATES[state][3]) + PAD_R
        self.setFixedSize(w, HEIGHT)

    def _set_state(self, state: str) -> None:
        self._state = state
        self._resize_for(state)
        self.update()

    def set_busy(self, busy: bool) -> None:
        if busy:
            self._done_timer.stop()
            self._set_state("busy")
            self._spin.start()
        else:
            self._spin.stop()
            if self._state == "busy":
                self._set_state("ready")

    def show_done(self, ms: int = 1600) -> None:
        self._spin.stop()
        self._set_state("done")
        self._done_timer.start(ms)

    def _done_over(self) -> None:
        self._set_state("ready")
        self.done_finished.emit()

    def reset(self) -> None:
        self._spin.stop()
        self._done_timer.stop()
        self._set_state("ready")

    def _tick(self) -> None:
        self._angle = (self._angle + 12) % 360
        self.update()

    # ---------- painting ----------
    def paintEvent(self, _):
        key = "hover" if self._state == "ready" and self._hover else self._state
        bg, border, fg, label = STATES[key]
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(0.5, 0.5, self.width() - 1, self.height() - 1)
        p.setPen(QPen(QColor(border), 1))
        p.setBrush(QColor(bg))
        p.drawRoundedRect(r, r.height() / 2, r.height() / 2)

        cx, cy = PAD_L + ICON / 2, self.height() / 2
        if self._state == "busy":
            pen = QPen(QColor(fg), 2)
            pen.setCapStyle(Qt.RoundCap)
            p.setPen(pen)
            p.setBrush(Qt.NoBrush)
            p.drawArc(QRectF(cx - 6, cy - 6, 12, 12), -self._angle * 16, 270 * 16)
        elif self._state == "done":
            pen = QPen(QColor(fg), 2)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            p.setPen(pen)
            p.drawPolyline([QPointF(cx - 5, cy), QPointF(cx - 1.5, cy + 3.5), QPointF(cx + 5, cy - 4)])
        else:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#534AB7") if key == "ready" else QColor(fg))
            p.drawPath(sparkle_path(cx - 1, cy + 1, 6.5))
            p.drawPath(sparkle_path(cx + 5, cy - 5, 2.8))

        p.setPen(QColor(fg))
        p.setFont(self._font)
        text_rect = QRectF(PAD_L + ICON + GAP, 0, self.width(), self.height())
        p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label)
        p.end()

    # ---------- input ----------
    def mousePressEvent(self, e):
        if self._state in ("busy", "done"):
            return
        if e.button() == Qt.LeftButton:
            self.clicked.emit()
        elif e.button() == Qt.RightButton:
            self.right_clicked.emit(e.globalPosition().toPoint())

    def enterEvent(self, _):
        self._hover = True
        self.update()
        self.hover_changed.emit(True)

    def leaveEvent(self, _):
        self._hover = False
        self.update()
        self.hover_changed.emit(False)

    # ---------- placement (physical pixels from UI Automation) ----------
    def place(self, info: dict) -> None:
        self.target_hwnd = info.get("hwnd", 0)
        self.last_field = info.get("field")
        if not self.isVisible():
            self.reset()
            self.show()
        w, h = winstyle.window_size(self.hwnd)
        x, y = compute_position(info.get("field"), info.get("caret"), info.get("mouse", (0, 0)), w, h,
                                winstyle.work_area)
        winstyle.move_physical(self.hwnd, x, y)

    def physical_anchor(self) -> tuple[int, int]:
        import win32gui
        l, t, r, b = win32gui.GetWindowRect(self.hwnd)
        return r, b
