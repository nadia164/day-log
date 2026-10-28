"""All app logic lives here. The UI only calls these methods and listens
to the signals, so it never edits data (or the database) directly.

The store shows one day at a time (`day`), which defaults to today.
"""

from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date, datetime, timedelta

from PySide6.QtCore import QObject, Signal

from .database import Database, default_db_path
from .models import Accomplishment, WorkSession
from .reports import Report, build_report


class TodayStore(QObject):
    # Separate signals so each part of the UI only redraws what changed.
    sessions_changed = Signal()
    accomplishments_changed = Signal()
    day_changed = Signal()
    # Any saved change on any day (used by the Reports window).
    data_changed = Signal()

    def __init__(self, db: Database | None = None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._db = db if db is not None else Database(default_db_path())
        self._day = date.today()
        # Restored on startup, so closing the app doesn't clock you out.
        self._open_session = self._db.load_open_session()
        self._sessions: list[WorkSession] = []
        self._accomplishments: list[Accomplishment] = []
        self._load_day()

    def _load_day(self) -> None:
        self._sessions = self._db.load_sessions(self._day)
        self._accomplishments = self._db.load_accomplishments(self._day)

    # ---- reading -------------------------------------------------------

    @property
    def day(self) -> date:
        """The day currently on screen."""
        return self._day

    @property
    def is_today(self) -> bool:
        return self._day == date.today()

    @property
    def sessions(self) -> tuple[WorkSession, ...]:
        return tuple(self._sessions)

    @property
    def accomplishments(self) -> tuple[Accomplishment, ...]:
        return tuple(self._accomplishments)

    @property
    def active_session(self) -> WorkSession | None:
        """The running session, whichever day you're viewing."""
        return self._open_session

    @property
    def is_clocked_in(self) -> bool:
        return self._open_session is not None

    def total_worked(self, now: datetime) -> timedelta:
        """Total for the day on screen."""
        return sum((s.duration_at(now) for s in self._sessions), timedelta())

    def today_total(self, now: datetime) -> timedelta:
        """Total for today, even while a past day is on screen (used by the tray)."""
        sessions = self._sessions if self.is_today else self._db.load_sessions(date.today())
        return sum((s.duration_at(now) for s in sessions), timedelta())

    def has_accomplishments_today(self) -> bool:
        if self.is_today:
            return bool(self._accomplishments)
        return bool(self._db.load_accomplishments(date.today()))

    def report(self, start: date, end: date) -> Report:
        """Totals and per-day breakdown from start to end (inclusive)."""
        return build_report(
            self._db.load_sessions_range(start, end),
            self._db.load_accomplishments_range(start, end),
            start,
            end,
            datetime.now(),
        )

    def close(self) -> None:
        self._db.close()

    # ---- navigation ----------------------------------------------------

    def go_to_day(self, day: date) -> None:
        day = min(day, date.today())  # no future days
        if day == self._day:
            return
        self._day = day
        self._load_day()
        self.day_changed.emit()
        self.sessions_changed.emit()
        self.accomplishments_changed.emit()

    def previous_day(self) -> None:
        self.go_to_day(self._day - timedelta(days=1))

    def next_day(self) -> None:
        self.go_to_day(self._day + timedelta(days=1))

    def go_to_today(self) -> None:
        self.go_to_day(date.today())

    # ---- actions -------------------------------------------------------

    def time_in(self) -> None:
        if self.is_clocked_in:
            return
        self.go_to_today()  # new sessions always belong to today
        session = WorkSession(id=_new_id(), start=_now())
        self._db.insert_session(session)
        self._open_session = session
        self._sessions.append(session)
        self.sessions_changed.emit()
        self.data_changed.emit()

    def time_out(self) -> None:
        active = self._open_session
        if active is None:
            return
        closed = replace(active, end=_now())
        self._db.update_session_end(closed.id, closed.end)
        self._open_session = None
        self._sessions = [closed if s.id == closed.id else s for s in self._sessions]
        self.sessions_changed.emit()
        self.data_changed.emit()

    def discard_away_time(
        self, session_id: str, away_start: datetime, resume_at: datetime | None
    ) -> bool:
        """Remove time you were away from the running session.

        The session ends at `away_start`. If `resume_at` is given, a new session
        starts then (you're back and still working); otherwise you stay clocked out.
        Does nothing if that session is no longer the running one.
        """
        active = self._open_session
        if active is None or active.id != session_id:
            return False

        away_start = max(away_start.replace(microsecond=0), active.start)
        if away_start <= active.start:
            # Away the whole time (e.g. clocked in, then walked off): drop it.
            self._db.delete_session(active.id)
        else:
            self._db.update_session_end(active.id, away_start)
        self._open_session = None

        if resume_at is not None:
            session = WorkSession(id=_new_id(), start=resume_at.replace(microsecond=0))
            self._db.insert_session(session)
            self._open_session = session

        self._load_day()  # the change may touch today or an earlier day
        self.sessions_changed.emit()
        self.data_changed.emit()
        return True

    def add_accomplishment(self, text: str, day: date | None = None) -> bool:
        """Adds to `day`, or to the day on screen if not given (so you can
        backfill a past day). The tray passes today's date.
        Returns True if something was added (empty text is ignored)."""
        text = text.strip()
        if not text:
            return False
        day = day or self._day
        item = Accomplishment(id=_new_id(), day=day, text=text, created_at=_now())
        self._db.insert_accomplishment(item)
        if day == self._day:  # only update the list if it's the day on screen
            self._accomplishments.append(item)
            self.accomplishments_changed.emit()
        self.data_changed.emit()
        return True

    def remove_accomplishment(self, accomplishment_id: str) -> None:
        self._db.delete_accomplishment(accomplishment_id)
        self._accomplishments = [
            a for a in self._accomplishments if a.id != accomplishment_id
        ]
        self.accomplishments_changed.emit()
        self.data_changed.emit()


def _new_id() -> str:
    return uuid.uuid4().hex


def _now() -> datetime:
    """Current time to the second (what we store in the database)."""
    return datetime.now().replace(microsecond=0)