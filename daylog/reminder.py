"""End-of-day reminder: if you're still clocked in at END_OF_DAY_REMINDER
(e.g. 6:00 PM), Daylog asks whether to time out.

- Shows once per day, only while you're clocked in.
- "Remind me in 30 min" snoozes it; "Keep working" hides it until tomorrow.
- If you start Daylog after the reminder time while still clocked in,
  it shows right away.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Callable

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .formatting import format_duration, format_time
from .store import TodayStore

CHECK_SECONDS = 30


def parse_time(text: str) -> time:
    """'18:00' -> 18:00. 24-hour HH:MM."""
    hours, minutes = text.strip().split(":")
    return time(int(hours), int(minutes))


class EndOfDayReminder(QObject):
    due = Signal()

    def __init__(
        self,
        store: TodayStore,
        remind_at: time,
        snooze: timedelta,
        clock: Callable[[], datetime] = datetime.now,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._remind_at = remind_at
        self._snooze = snooze
        self._clock = clock  # injectable for tests

        self._done_for: date | None = None  # day already handled
        self._snoozed_until: datetime | None = None
        self._showing = False

        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_SECONDS * 1000)
        self._timer.timeout.connect(self.check)

    def start(self) -> None:
        self._timer.start()
        QTimer.singleShot(3000, self.check)  # catch "started after 6 PM" soon after launch

    def check(self) -> None:
        now = self._clock()
        today = now.date()
        if self._showing or self._done_for == today or not self._store.is_clocked_in:
            return
        if self._snoozed_until is not None:
            if now < self._snoozed_until:
                return
        elif now.time() < self._remind_at:
            return
        self._showing = True
        self.due.emit()

    # The dialog reports what you chose:
    def snoozed(self) -> None:
        self._showing = False
        self._snoozed_until = self._clock() + self._snooze

    def done_for_today(self) -> None:
        self._showing = False
        self._snoozed_until = None
        self._done_for = self._clock().date()


class ReminderDialog(QDialog):
    """Appears on top but does NOT take keyboard focus, so it can't
    swallow what you're typing in another app."""

    time_out_chosen = Signal()
    snooze_chosen = Signal()
    keep_working_chosen = Signal()

    def __init__(self, store: TodayStore, snooze_minutes: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self.setObjectName("quickAdd")
        self.setWindowTitle("Daylog")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setMinimumWidth(460)

        self._title = QLabel()
        self._title.setObjectName("cardTitle")
        self._detail = QLabel()
        self._detail.setObjectName("muted")
        self._detail.setWordWrap(True)

        keep = QPushButton("Keep working")
        keep.setObjectName("secondaryButton")
        keep.clicked.connect(self._keep_working)
        snooze = QPushButton(f"Remind me in {snooze_minutes} min")
        snooze.setObjectName("secondaryButton")
        snooze.clicked.connect(self._snooze)
        time_out = QPushButton("Time Out")
        time_out.setObjectName("addButton")
        time_out.clicked.connect(self._time_out)
        # No default button on purpose: an Enter meant for another app must not clock you out.
        for button in (keep, snooze, time_out):
            button.setAutoDefault(False)
            button.setCursor(Qt.CursorShape.PointingHandCursor)

        buttons = QHBoxLayout()
        buttons.setSpacing(8)
        buttons.addWidget(keep)
        buttons.addStretch()
        buttons.addWidget(snooze)
        buttons.addWidget(time_out)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)
        layout.addWidget(self._title)
        layout.addWidget(self._detail)
        layout.addSpacing(6)
        layout.addLayout(buttons)

    def show_reminder(self) -> None:
        now = datetime.now()
        active = self._store.active_session
        since = format_time(active.start) if active else "earlier"
        lines = [
            f"Clocked in since {since}. {format_duration(self._store.today_total(now))} worked today."
        ]
        if not self._store.has_accomplishments_today():
            lines.append("No accomplishments logged today yet.")
        self._title.setText(f"It's {format_time(now)}. Still working?")
        self._detail.setText("\n".join(lines))
        self.adjustSize()
        self.show()
        self.raise_()  # on top, but focus stays where it was

    def reject(self) -> None:
        # X button or Esc = snooze, so the reminder isn't lost.
        # (QDialog routes both through reject().)
        self._finish(self.snooze_chosen)

    def _finish(self, signal: Signal) -> None:
        self.hide()
        signal.emit()

    def _time_out(self) -> None:
        self._finish(self.time_out_chosen)

    def _snooze(self) -> None:
        self._finish(self.snooze_chosen)

    def _keep_working(self) -> None:
        self._finish(self.keep_working_chosen)