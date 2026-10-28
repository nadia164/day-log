"""Asks "Time In now?" / "Time Out now?" before the hotkey changes anything,
so an accidental Ctrl+Alt+T is harmless.

Enter = confirm · Esc or Cancel = do nothing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .formatting import format_duration, format_time
from .qt_utils import bring_to_front
from .store import TodayStore


class ConfirmClockDialog(QDialog):
    def __init__(
        self,
        store: TodayStore,
        on_confirmed: Callable[[], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._on_confirmed = on_confirmed
        self.setObjectName("quickAdd")  # same background style as the quick-add popup
        self.setWindowTitle("Daylog")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(380)

        self._title = QLabel()
        self._title.setObjectName("cardTitle")
        self._detail = QLabel()
        self._detail.setObjectName("muted")
        self._detail.setWordWrap(True)

        self._cancel = QPushButton("Cancel")
        self._cancel.setObjectName("secondaryButton")
        self._cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._cancel.clicked.connect(self.reject)

        self._confirm = QPushButton()
        self._confirm.setObjectName("addButton")
        self._confirm.setCursor(Qt.CursorShape.PointingHandCursor)
        self._confirm.setDefault(True)  # Enter presses this
        self._confirm.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(self._cancel)
        buttons.addWidget(self._confirm)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(self._title)
        layout.addWidget(self._detail)
        layout.addSpacing(6)
        layout.addLayout(buttons)

        self.accepted.connect(self._on_confirmed)

    def ask(self) -> None:
        """Show the question for the current state. If it's already open,
        just bring it back to the front (pressing the hotkey twice won't toggle)."""
        if self.isVisible():
            bring_to_front(self)
            return

        now = datetime.now()
        active = self._store.active_session
        if active:
            self._title.setText("Time out now?")
            self._detail.setText(
                f"Clocked in since {format_time(active.start)}. "
                f"{format_duration(self._store.today_total(now))} worked today."
            )
            self._confirm.setText("Time Out")
        else:
            self._title.setText("Time in now?")
            self._detail.setText(f"Starts a new session at {format_time(now)}.")
            self._confirm.setText("Time In")

        self.adjustSize()
        bring_to_front(self)
        self._confirm.setFocus()