"""App and tray icons, drawn in code so there are no image files to manage.
build.py exports the app icon to assets/daylog.ico for the .exe and installer."""

from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import QBuffer, QIODevice, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap

INDIGO = QColor("#4f46e5")
GREEN = QColor("#22c55e")


def _draw(size: int, show_dot: bool) -> QPixmap:
    """Indigo rounded square with a white clock. Optional green 'clocked in' dot."""
    s = float(size)
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Background
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(INDIGO)
    p.drawRoundedRect(QRectF(0, 0, s, s), s * 0.22, s * 0.22)

    # Clock face and hands
    pen = QPen(QColor("white"))
    pen.setWidthF(max(1.5, s * 0.08))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    center = QPointF(s / 2, s / 2)
    radius = s * 0.3
    p.drawEllipse(center, radius, radius)
    p.drawLine(center, QPointF(s / 2, s / 2 - radius * 0.6))
    p.drawLine(center, QPointF(s / 2 + radius * 0.45, s / 2))

    # Status dot (bottom-right corner)
    if show_dot:
        dot_r = s * 0.2
        dot_center = QPointF(s - dot_r, s - dot_r)
        p.setPen(QPen(QColor("white"), max(1.0, s * 0.05)))
        p.setBrush(GREEN)
        p.drawEllipse(dot_center, dot_r, dot_r)

    p.end()
    return pixmap


def _icon(show_dot: bool, sizes: tuple[int, ...]) -> QIcon:
    icon = QIcon()
    for size in sizes:
        icon.addPixmap(_draw(size, show_dot))
    return icon


def make_app_icon() -> QIcon:
    """Window / taskbar icon."""
    return _icon(False, (16, 24, 32, 48, 64, 128, 256))


def make_tray_icon(clocked_in: bool) -> QIcon:
    """Tray icon. Shows a green dot while you're clocked in."""
    return _icon(clocked_in, (16, 20, 24, 32, 40, 48, 64))


def save_ico(path: Path, sizes: tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64, 128, 256)) -> None:
    """Write a Windows .ico file with every size (for the .exe and installer).

    An .ico is a small header, one 16-byte entry per size, then the images.
    Each image is stored as PNG, which Windows supports since Vista.
    """
    images = []
    for size in sizes:
        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        _draw(size, show_dot=False).save(buffer, "PNG")
        images.append((size, bytes(buffer.data())))

    header = struct.pack("<HHH", 0, 1, len(images))  # reserved, type 1 = icon, count
    offset = 6 + 16 * len(images)
    entries, data = b"", b""
    for size, png in images:
        side = 0 if size >= 256 else size  # 0 means 256 in the .ico format
        entries += struct.pack("<BBBBHHII", side, side, 0, 0, 1, 32, len(png), offset + len(data))
        data += png
    Path(path).write_bytes(header + entries + data)