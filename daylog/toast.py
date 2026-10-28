"""Daylog's own pop-up notification (bottom-right, above the taskbar).

We draw this ourselves instead of using Windows notifications, because
Windows can silently hide those (Do Not Disturb, notification settings
for python.exe, etc.). This one always shows.
"""

from __future__ import annotations

from PySide6.QtCore import QPropertyAnimation, Qt, QTimer
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .qt_utils import repolish

MARGIN = 16  # gap from the screen edge / taskbar


class Toast(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.Tool  # no taskbar button
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        # Don't steal focus from whatever app you're typing in.
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        # Transparent window so the card's rounded corners look clean.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(320)

        self._dot = QLabel()
        self._dot.setObjectName("toastDot")
        self._dot.setFixedSize(10, 10)
        self._title = QLabel()
        self._title.setObjectName("toastTitle")
        self._message = QLabel()
        self._message.setObjectName("toastMessage")
        self._message.setWordWrap(True)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_row.addWidget(self._dot)
        title_row.addWidget(self._title, 1)

        card = QFrame()
        card.setObjectName("toast")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(4)
        card_layout.addLayout(title_row)
        card_layout.addWidget(self._message)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(card)

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._fade_out)

        self._fade = QPropertyAnimation(self, b"windowOpacity", self)
        self._fade.setDuration(250)
        self._fade.finished.connect(self._on_fade_finished)

    def show_message(
        self, title: str, message: str, kind: str = "info", duration_ms: int = 3000
    ) -> None:
        """kind: "on" (green dot), "off" (gray dot), or "info" (indigo dot)."""
        self._title.setText(title)
        self._message.setText(message)
        self._message.setVisible(bool(message))
        self._dot.setProperty("kind", kind)
        repolish(self._dot)

        self.adjustSize()
        self._move_to_corner()

        # Fade in (or stay visible if a toast is already showing).
        self._fade.stop()
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        self._hide_timer.start(duration_ms)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self._fade_out()  # click to dismiss

    def _move_to_corner(self) -> None:
        screen = QGuiApplication.primaryScreen()
        if screen is None:
            return
        area = screen.availableGeometry()  # excludes the taskbar
        self.move(
            area.right() - self.width() - MARGIN,
            area.bottom() - self.height() - MARGIN,
        )

    def _fade_out(self) -> None:
        self._hide_timer.stop()
        self._fade.stop()
        self._fade.setStartValue(self.windowOpacity())
        self._fade.setEndValue(0.0)
        self._fade.start()

    def _on_fade_finished(self) -> None:
        if self.windowOpacity() == 0.0:
            self.hide()