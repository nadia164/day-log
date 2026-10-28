"""SQLite storage. The only file that knows SQL exists.

The database lives in your user AppData folder, e.g.
C:\\Users\\<you>\\AppData\\Roaming\\Daylog\\daylog.db
so it survives reinstalls and isn't mixed in with the code.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path

from PySide6.QtCore import QStandardPaths

from .models import Accomplishment, WorkSession

# Each entry upgrades the database by one version. Never edit an old entry
# once it has shipped; add a new one instead. SQLite's built-in
# `PRAGMA user_version` remembers which ones already ran.
MIGRATIONS: list[list[str]] = [
    # version 1: sessions + accomplishments
    [
        """
        CREATE TABLE sessions (
            id         TEXT PRIMARY KEY,
            day        TEXT NOT NULL,   -- YYYY-MM-DD, the day it started
            start_time TEXT NOT NULL,   -- ISO 8601 local time
            end_time   TEXT             -- NULL while clocked in
        )
        """,
        "CREATE INDEX idx_sessions_day ON sessions(day)",
        """
        CREATE TABLE accomplishments (
            id         TEXT PRIMARY KEY,
            day        TEXT NOT NULL,
            text       TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """,
        "CREATE INDEX idx_accomplishments_day ON accomplishments(day)",
    ],
]


def default_db_path() -> Path:
    """Per-user app data folder. Needs QApplication's name set first (main.py does)."""
    folder = QStandardPaths.writableLocation(
        QStandardPaths.StandardLocation.AppDataLocation
    )
    return Path(folder) / "daylog.db"


class Database:
    def __init__(self, path: Path | str) -> None:
        if str(path) != ":memory:":  # ":memory:" is handy for tests
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.row_factory = sqlite3.Row  # rows act like dicts
        self._migrate()

    def close(self) -> None:
        self._conn.close()

    # ---- schema --------------------------------------------------------

    def _migrate(self) -> None:
        current = self._conn.execute("PRAGMA user_version").fetchone()[0]
        for version, statements in enumerate(MIGRATIONS, start=1):
            if version <= current:
                continue
            # All-or-nothing: a failed migration leaves the old schema intact.
            with self._conn:
                self._conn.execute("BEGIN")
                for sql in statements:
                    self._conn.execute(sql)
                self._conn.execute(f"PRAGMA user_version = {version}")

    # ---- sessions ------------------------------------------------------

    def load_sessions(self, day: date) -> list[WorkSession]:
        rows = self._conn.execute(
            "SELECT id, start_time, end_time FROM sessions "
            "WHERE day = ? ORDER BY start_time",
            (day.isoformat(),),
        ).fetchall()
        return [_row_to_session(r) for r in rows]

    def load_sessions_range(self, start: date, end: date) -> list[WorkSession]:
        """Sessions whose day is between start and end (inclusive)."""
        rows = self._conn.execute(
            "SELECT id, start_time, end_time FROM sessions "
            "WHERE day BETWEEN ? AND ? ORDER BY start_time",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [_row_to_session(r) for r in rows]

    def load_open_session(self) -> WorkSession | None:
        """The session you're clocked in on, even if it started on an earlier day."""
        row = self._conn.execute(
            "SELECT id, start_time, end_time FROM sessions "
            "WHERE end_time IS NULL ORDER BY start_time DESC LIMIT 1"
        ).fetchone()
        return _row_to_session(row) if row else None

    def insert_session(self, session: WorkSession) -> None:
        with self._conn:  # commits immediately, so a crash loses nothing
            self._conn.execute(
                "INSERT INTO sessions (id, day, start_time, end_time) "
                "VALUES (?, ?, ?, ?)",
                (
                    session.id,
                    session.day.isoformat(),
                    session.start.isoformat(),
                    _iso_or_none(session.end),
                ),
            )

    def update_session_end(self, session_id: str, end: datetime) -> None:
        with self._conn:
            self._conn.execute(
                "UPDATE sessions SET end_time = ? WHERE id = ?",
                (end.isoformat(), session_id),
            )

    def delete_session(self, session_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))

    # ---- accomplishments -----------------------------------------------

    def load_accomplishments(self, day: date) -> list[Accomplishment]:
        return self.load_accomplishments_range(day, day)

    def load_accomplishments_range(self, start: date, end: date) -> list[Accomplishment]:
        """Accomplishments whose day is between start and end (inclusive)."""
        rows = self._conn.execute(
            "SELECT id, day, text, created_at FROM accomplishments "
            "WHERE day BETWEEN ? AND ? ORDER BY day, created_at",
            (start.isoformat(), end.isoformat()),
        ).fetchall()
        return [
            Accomplishment(
                id=r["id"],
                day=date.fromisoformat(r["day"]),
                text=r["text"],
                created_at=datetime.fromisoformat(r["created_at"]),
            )
            for r in rows
        ]

    def insert_accomplishment(self, item: Accomplishment) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT INTO accomplishments (id, day, text, created_at) "
                "VALUES (?, ?, ?, ?)",
                (
                    item.id,
                    item.day.isoformat(),
                    item.text,
                    item.created_at.isoformat(),
                ),
            )

    def delete_accomplishment(self, accomplishment_id: str) -> None:
        with self._conn:
            self._conn.execute(
                "DELETE FROM accomplishments WHERE id = ?", (accomplishment_id,)
            )


def _row_to_session(row: sqlite3.Row) -> WorkSession:
    return WorkSession(
        id=row["id"],
        start=datetime.fromisoformat(row["start_time"]),
        end=datetime.fromisoformat(row["end_time"]) if row["end_time"] else None,
    )


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None