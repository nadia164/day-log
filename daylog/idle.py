"""Idle detection: notices when you've stepped away while clocked in.

How it works:
- Windows tracks the time of your last mouse/keyboard input. We read it with
  GetLastInputInfo (via ctypes) every few seconds.
- If there's been no input for IDLE_MINUTES, you're "away" since that last input.
- As soon as there's new input, you're "back", and we emit `returned`.
- Sleep/hibernate: our timer can't run while the PC sleeps, so a big gap
  between two checks also counts as being away.

On macOS/Linux idle_seconds() returns 0, so nothing is ever detected.
"""

from __future__ import annotations

import ctypes
import sys
from datetime import datetime, timedelta
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal

from .store import TodayStore

IS_WINDOWS = sys.platform == "win32"

POLL_SECONDS = 5
# Input within this many seconds means you're back at the keyboard.
BACK_SECONDS = 10


if IS_WINDOWS:
    from ctypes import wintypes

    class _LastInputInfo(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    _user32 = ctypes.WinDLL("user32")
    _kernel32 = ctypes.WinDLL("kernel32")
    _kernel32.GetTickCount.restype = wintypes.DWORD


def idle_seconds() -> float:
    """Seconds since the last mouse or keyboard input anywhere on the PC."""
    if not IS_WINDOWS:
        return 0.0
    info = _LastInputInfo()
    info.cbSize = ctypes.sizeof(info)
    if not _user32.GetLastInputInfo(ctypes.byref(info)):
        return 0.0
    # Both are milliseconds since boot (32-bit, wraps every ~49 days; the mask handles it).
    millis = (_kernel32.GetTickCount() - info.dwTime) & 0xFFFFFFFF
    return millis / 1000.0


class IdleMonitor(QObject):
    # (session id, away since, back at)
    returned = Signal(str, datetime, datetime)

    def __init__(
        self,
        store: TodayStore,
        threshold: timedelta,
        get_idle_seconds: Callable[[], float] = idle_seconds,
        clock: Callable[[], datetime] = datetime.now,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._threshold = threshold
        # Injectable so tests can fake time and input.
        self._get_idle_seconds = get_idle_seconds
        self._clock = clock

        self._away_since: datetime | None = None
        self._away_session_id: str | None = None
        self._last_poll: datetime | None = None
        self._paused = False

        self._timer = QTimer(self)
        self._timer.setInterval(POLL_SECONDS * 1000)
        self._timer.timeout.connect(self.poll)

    @property
    def supported(self) -> bool:
        return IS_WINDOWS

    def start(self) -> None:
        self._last_poll = self._clock()
        self._timer.start()

    def pause(self) -> None:
        """Stop detecting while the 'You were away' dialog is open."""
        self._paused = True
        self._away_since = None

    def resume(self) -> None:
        self._paused = False
        self._last_poll = self._clock()

    def poll(self) -> None:
        now = self._clock()
        gap = now - self._last_poll if self._last_poll else timedelta()
        self._last_poll = now

        active = self._store.active_session
        if self._paused or active is None:
            self._away_since = None
            return

        idle = timedelta(seconds=self._get_idle_seconds())

        # 1) Notice that you've gone away.
        if self._away_since is None:
            if idle >= self._threshold:
                self._away_since = now - idle  # = your last input
            elif gap >= self._threshold:
                self._away_since = now - gap  # PC was asleep
            if self._away_since is not None:
                self._away_session_id = active.id

        # 2) Notice that you're back.
        if self._away_since is not None and idle <= timedelta(seconds=BACK_SECONDS):
            away_since = max(self._away_since, active.start)
            session_id = self._away_session_id or active.id
            self._away_since = None
            self._away_session_id = None
            self.returned.emit(session_id, away_since, now - idle)