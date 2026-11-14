"""App icon drawn at runtime (so no image files are required)."""
from __future__ import annotations

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QLinearGradient, QPainter, QPainterPath, QPixmap

ACCENT_A = QColor("#7C4DFF")
ACCENT_B = QColor("#448AFF")


def sparkle_path(cx: float, cy: float, r: float) -> QPainterPath:
    """A 4-point sparkle star."""
    p = QPainterPath()
    k = r * 0.28
    p.moveTo(cx, cy - r)
    p.quadTo(cx + k * 0.3, cy - k * 0.3, cx + r, cy)
    p.quadTo(cx + k * 0.3, cy + k * 0.3, cx, cy + r)
    p.quadTo(cx - k * 0.3, cy + k * 0.3, cx - r, cy)
    p.quadTo(cx - k * 0.3, cy - k * 0.3, cx, cy - r)
    p.closeSubpath()
    return p


def draw_badge(painter: QPainter, rect: QRectF, paused: bool = False) -> None:
    painter.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(rect.topLeft(), rect.bottomRight())
    if paused:
        g.setColorAt(0, QColor("#9E9E9E"))
        g.setColorAt(1, QColor("#616161"))
    else:
        g.setColorAt(0, ACCENT_A)
        g.setColorAt(1, ACCENT_B)
    painter.setPen(Qt.NoPen)
    painter.setBrush(g)
    painter.drawEllipse(rect)
    w = rect.width()
    painter.setBrush(QColor("white"))
    painter.drawPath(sparkle_path(rect.center().x() - w * 0.06, rect.center().y() + w * 0.04, w * 0.27))
    painter.drawPath(sparkle_path(rect.center().x() + w * 0.2, rect.center().y() - w * 0.2, w * 0.11))


def app_icon(paused: bool = False) -> QIcon:
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        pm = QPixmap(size, size)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        draw_badge(p, QRectF(0.5, 0.5, size - 1, size - 1), paused)
        p.end()
        icon.addPixmap(pm)
    return icon


def save_ico(path: str) -> None:
    """Used by the build script to produce assets/icon.ico."""
    pm = app_icon().pixmap(256, 256)
    pm.save(path, "ICO")


if __name__ == "__main__":  # pragma: no cover
    import sys

    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication(sys.argv)
    save_ico(sys.argv[1] if len(sys.argv) > 1 else "assets/icon.ico")
