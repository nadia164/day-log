"""Plain data classes. No Qt here, so they're easy to test and reuse."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta


@dataclass(frozen=True)
class WorkSession:
    """One Time In -> Time Out block. A day can have several."""

    id: str
    start: datetime
    end: datetime | None = None  # None while you're still clocked in

    @property
    def is_active(self) -> bool:
        return self.end is None

    @property
    def day(self) -> date:
        """A session belongs to the day it started on."""
        return self.start.date()

    def duration_at(self, now: datetime) -> timedelta:
        """For a running session, measures up to `now` so the timer ticks live."""
        return (self.end or now) - self.start


@dataclass(frozen=True)
class Accomplishment:
    """Something you got done on a given day."""

    id: str
    day: date
    text: str
    created_at: datetime