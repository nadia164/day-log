"""Clock-in status, the live "worked" timer, the Time In / Time Out
button, and the sessions for the day on screen."""

from __future__ import annotations

from datetime import date, datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .formatting import format_duration, format_short_date, format_time
from .qt_utils import clear_layout, repolish
from .store import TodayStore


class SessionCard(QFrame):
    def __init__(self, store: TodayStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._store = store
        self._duration_labels: list[QLabel] = []

        # Status row: colored dot + text
        self._status_dot = QLabel()
        self._status_dot.setObjectName("statusDot")
        self._status_dot.setFixedSize(10, 10)
        self._status_text = QLabel()
        self._status_text.setObjectName("cardTitle")

        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addWidget(self._status_dot)
        status_row.addWidget(self._status_text)
        status_row.addStretch()

        # Big timer
        self._caption = QLabel()
        self._caption.setObjectName("caption")
        self._timer_label = QLabel()
        self._timer_label.setObjectName("timer")

        # Time In / Time Out button
        self._clock_button = QPushButton()
        self._clock_button.setObjectName("clockButton")
        self._clock_button.setMinimumHeight(44)
        self._clock_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._clock_button.clicked.connect(self._on_clock_clicked)

        # Sessions list (hidden until there's at least one)
        self._divider = QFrame()
        self._divider.setObjectName("divider")
        self._divider.setFixedHeight(1)
        self._sessions_title = QLabel("Sessions")
        self._sessions_title.setObjectName("sectionTitle")
        self._sessions_list = QVBoxLayout()
        self._sessions_list.setSpacing(6)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addLayout(status_row)
        layout.addSpacing(4)
        layout.addWidget(self._caption)
        layout.addWidget(self._timer_label)
        layout.addSpacing(4)
        layout.addWidget(self._clock_button)
        layout.addSpacing(4)
        layout.addWidget(self._divider)
        layout.addWidget(self._sessions_title)
        layout.addLayout(self._sessions_list)

        # Tick once a second so the running timer updates.
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._on_tick)
        self._ticker.start()

        # Changing the day also emits sessions_changed, so this covers both.
        store.sessions_changed.connect(self._refresh)
        self._refresh()

    # ---- events --------------------------------------------------------

    def _on_clock_clicked(self) -> None:
        if self._store.is_clocked_in:
            self._store.time_out()
        else:
            self._store.time_in()

    def _on_tick(self) -> None:
        if self._store.is_clocked_in:
            self._update_times()

    # ---- drawing -------------------------------------------------------

    def _refresh(self) -> None:
        """Rebuild everything that depends on the list of sessions."""
        active = self._store.active_session

        self._status_dot.setProperty("active", active is not None)
        repolish(self._status_dot)
        self._status_text.setText(_status_text(active.start) if active else "Not clocked in")

        self._caption.setText("Worked today" if self._store.is_today else "Worked")

        self._clock_button.setText("Time Out" if active else "Time In")
        self._clock_button.setProperty("clockedIn", active is not None)
        repolish(self._clock_button)

        clear_layout(self._sessions_list)
        self._duration_labels = []
        for session in self._store.sessions:
            end_text = "now" if session.end is None else format_time(session.end)
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.addWidget(QLabel(f"{format_time(session.start)} – {end_text}"))
            row_layout.addStretch()
            duration = QLabel()
            duration.setObjectName("muted")
            row_layout.addWidget(duration)
            self._sessions_list.addWidget(row)
            self._duration_labels.append(duration)

        has_sessions = bool(self._store.sessions)
        self._divider.setVisible(has_sessions)
        self._sessions_title.setVisible(has_sessions)

        self._update_times()

    def _update_times(self) -> None:
        """Cheap update for the per-second tick: only the numbers change."""
        now = datetime.now()
        self._timer_label.setText(format_duration(self._store.total_worked(now)))
        for session, label in zip(self._store.sessions, self._duration_labels):
            label.setText(format_duration(session.duration_at(now)))


def _status_text(start: datetime) -> str:
    # Mention the date if you clocked in on an earlier day and never clocked out.
    if start.date() != date.today():
        return f"Clocked in since {format_short_date(start)}, {format_time(start)}"
    return f"Clocked in since {format_time(start)}"