"""Hours-per-day bar chart, drawn with QPainter (no chart library needed).

Design rules: one color (it's one series, so no legend; the card title names it),
thin bars with rounded tops and square bottoms, faint gridlines, only the
longest day labeled, exact values on hover.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QToolTip, QWidget

BAR = QColor("#4f46e5")
BAR_HOVER = QColor("#3730a3")
HOVER_BAND = QColor("#eef0fb")
GRID = QColor("#e4e6ef")
TEXT = QColor("#1f2333")
MUTED = QColor("#6b7085")

MAX_BAR_WIDTH = 24
CORNER = 4
LEFT_AXIS = 40
BOTTOM_AXIS = 26
TOP_PAD = 24


@dataclass(frozen=True)
class Bar:
    label: str  # under the bar, e.g. "Mon" or "15" ("" to skip)
    tooltip: str  # shown on hover
    hours: float | None  # None = future day (no bar, no hover)
    emphasize_label: bool = False  # e.g. today


def nice_step(max_value: float) -> float:
    """A round gridline step that gives about 3 to 5 lines."""
    for step in (0.5, 1, 2, 3, 4, 6, 8, 12, 24, 48, 96):
        if max_value / step <= 5:
            return step
    return math.ceil(max_value / 5)


class BarChart(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._bars: list[Bar] = []
        self._hover: int | None = None
        self.setMouseTracking(True)
        self.setMinimumHeight(220)

    def set_bars(self, bars: list[Bar]) -> None:
        self._bars = bars
        self._hover = None
        self.update()

    # ---- geometry ------------------------------------------------------

    def _plot(self) -> QRectF:
        return QRectF(
            LEFT_AXIS, TOP_PAD, self.width() - LEFT_AXIS - 4, self.height() - TOP_PAD - BOTTOM_AXIS
        )

    def _scale(self) -> tuple[float, float]:
        """(top value of the y axis, gridline step), in hours."""
        highest = max((b.hours or 0 for b in self._bars), default=0)
        step = nice_step(max(highest, 1))
        return step * math.ceil(max(highest, 1) / step), step

    def _slot(self, index: int, plot: QRectF) -> QRectF:
        width = plot.width() / max(len(self._bars), 1)
        return QRectF(plot.left() + index * width, plot.top(), width, plot.height())

    # ---- drawing -------------------------------------------------------

    def paintEvent(self, event) -> None:
        if not self._bars:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        plot = self._plot()
        top, step = self._scale()

        small = QFont(self.font())
        small.setPointSizeF(max(8.0, self.font().pointSizeF() - 1))
        p.setFont(small)

        # Gridlines + y labels (hairline, solid, recessive)
        value = 0.0
        while value <= top + 1e-9:
            y = plot.bottom() - value / top * plot.height()
            p.setPen(QPen(GRID, 1))
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            p.setPen(MUTED)
            label = f"{value:g}h"
            p.drawText(QRectF(0, y - 8, LEFT_AXIS - 8, 16),
                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, label)
            value += step

        longest = max(
            (i for i, b in enumerate(self._bars) if b.hours),
            key=lambda i: self._bars[i].hours or 0,
            default=None,
        )

        for i, bar in enumerate(self._bars):
            slot = self._slot(i, plot)

            if i == self._hover and bar.hours is not None:
                p.fillRect(slot, HOVER_BAND)

            # Bar: <= 24px wide, rounded 4px top, square at the baseline
            if bar.hours:
                width = min(MAX_BAR_WIDTH, slot.width() * 0.6)
                height = bar.hours / top * plot.height()
                rect = QRectF(slot.center().x() - width / 2, plot.bottom() - height, width, height)
                p.fillPath(_rounded_top(rect, min(CORNER, width / 2, height)),
                           BAR_HOVER if i == self._hover else BAR)

                # Label only the longest day (text in text color, never the bar color)
                if i == longest:
                    p.setPen(TEXT)
                    p.drawText(QRectF(slot.center().x() - 40, rect.top() - 20, 80, 18),
                               Qt.AlignmentFlag.AlignCenter, f"{bar.hours:.1f}h")

            # X label
            if bar.label:
                font = QFont(small)
                font.setBold(bar.emphasize_label)
                p.setFont(font)
                p.setPen(TEXT if bar.emphasize_label else MUTED)
                p.drawText(QRectF(slot.center().x() - 24, plot.bottom() + 4, 48, BOTTOM_AXIS - 4),
                           Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop, bar.label)
                p.setFont(small)
        p.end()

    # ---- hover ---------------------------------------------------------

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        plot = self._plot()
        x = event.position().x()
        index = None
        if self._bars and plot.left() <= x <= plot.right():
            # The whole column is the hover target, not just the (thin) bar.
            index = min(int((x - plot.left()) / (plot.width() / len(self._bars))), len(self._bars) - 1)
            if self._bars[index].hours is None:
                index = None
        if index != self._hover:
            self._hover = index
            self.update()
        if index is None:
            QToolTip.hideText()
        else:
            QToolTip.showText(event.globalPosition().toPoint(), self._bars[index].tooltip, self)

    def leaveEvent(self, event) -> None:
        self._hover = None
        QToolTip.hideText()
        self.update()


def _rounded_top(rect: QRectF, radius: float) -> QPainterPath:
    path = QPainterPath()
    path.moveTo(rect.left(), rect.bottom())
    path.lineTo(rect.left(), rect.top() + radius)
    path.quadTo(rect.left(), rect.top(), rect.left() + radius, rect.top())
    path.lineTo(rect.right() - radius, rect.top())
    path.quadTo(rect.right(), rect.top(), rect.right(), rect.top() + radius)
    path.lineTo(rect.right(), rect.bottom())
    path.closeSubpath()
    return path