"""'You were away' dialog: keep or remove the time you were away.

Keep time (Enter / Esc / X) .......... nothing changes
Remove, keep working ................. clocks out at the time you left, back in when you returned
Remove and time out .................. clocks out at the time you left
"""

from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .formatting import format_time
from .qt_utils import bring_to_front
from .store import TodayStore


class IdleDialog(QDialog):
    # Emitted after a choice that removed time: (removed duration, still clocked in?)
    time_removed = Signal(timedelta, bool)

    def __init__(self, store: TodayStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self._session_id = ""
        self._away_since = datetime.now()
        self._back_at = datetime.now()

        self.setObjectName("quickAdd")  # same background as the other popups
        self.setWindowTitle("Daylog")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(460)

        self._title = QLabel()
        self._title.setObjectName("cardTitle")
        self._detail = QLabel()
        self._detail.setObjectName("muted")
        self._detail.setWordWrap(True)

        self._stop_button = QPushButton()
        self._stop_button.setObjectName("secondaryButton")
        self._stop_button.clicked.connect(self._remove_and_time_out)

        self._resume_button = QPushButton("Remove, keep working")
        self._resume_button.setObjectName("secondaryButton")
        self._resume_button.clicked.connect(self._remove_and_resume)

        self._keep_button = QPushButton("Keep time")
        self._keep_button.setObjectName("addButton")
        self._keep_button.setDefault(True)  # Enter = the safe choice
        self._keep_button.clicked.connect(self.reject)

        for button in (self._stop_button, self._resume_button, self._keep_button):
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(self._stop_button)
        buttons.addStretch()
        buttons.addWidget(self._resume_button)
        buttons.addWidget(self._keep_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(self._title)
        layout.addWidget(self._detail)
        layout.addSpacing(6)
        layout.addLayout(buttons)

    def ask(self, session_id: str, away_since: datetime, back_at: datetime) -> None:
        self._session_id = session_id
        self._away_since = away_since
        self._back_at = back_at

        self._title.setText(f"You were away for {format_away(back_at - away_since)}")
        self._detail.setText(
            f"No activity from {format_time(away_since)} to {format_time(back_at)} "
            "while you were clocked in. Keep that time in your session?"
        )
        self._stop_button.setText(f"Time out at {format_time(away_since)}")

        self.adjustSize()
        bring_to_front(self)
        self._keep_button.setFocus()

    def _remove_and_resume(self) -> None:
        if self._store.discard_away_time(self._session_id, self._away_since, self._back_at):
            self.time_removed.emit(self._back_at - self._away_since, True)
        self.accept()

    def _remove_and_time_out(self) -> None:
        if self._store.discard_away_time(self._session_id, self._away_since, None):
            self.time_removed.emit(self._back_at - self._away_since, False)
        self.accept()


def format_away(d: timedelta) -> str:
    """e.g. '25 min' or '1 hr 5 min'"""
    minutes = max(1, int(d.total_seconds() // 60))
    hours, minutes = divmod(minutes, 60)
    if hours and minutes:
        return f"{hours} hr {minutes} min"
    if hours:
        return f"{hours} hr"
    return f"{minutes} min"