"""Only one Daylog at a time.

If Daylog is already running (e.g. in the tray from Launch at startup) and you
open it again from a shortcut, the new copy just tells the running one to show
its window, then exits. No duplicate tray icons, no hotkey conflicts.

How: the first copy opens a named local channel (QLocalServer, a named pipe
on Windows). A second copy tries to connect to it; if that works, it sends
"show" and quits.
"""

from __future__ import annotations

import getpass
import sys
from typing import Callable

from PySide6.QtCore import QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

TIMEOUT_MS = 500


def _channel_name() -> str:
    # Per Windows user, so two people on the same PC each get their own Daylog.
    return f"daylog-{getpass.getuser()}"


APP_MUTEX = "DaylogAppMutex"
_mutex_handle = None


def hold_app_mutex() -> None:
    """A named Windows mutex that exists while Daylog runs. The installer and
    uninstaller check for it (AppMutex in installer.iss) and ask you to quit
    Daylog first, so files in use aren't replaced halfway."""
    global _mutex_handle
    if sys.platform == "win32" and _mutex_handle is None:
        import ctypes

        _mutex_handle = ctypes.windll.kernel32.CreateMutexW(None, False, APP_MUTEX)


def notify_running_instance() -> bool:
    """Returns True if another Daylog is running (and was asked to show itself)."""
    socket = QLocalSocket()
    socket.connectToServer(_channel_name())
    if not socket.waitForConnected(TIMEOUT_MS):
        return False
    if sys.platform == "win32":
        # Windows only lets the app you just clicked bring windows to the front.
        # This passes that permission on to the running Daylog.
        import ctypes

        ctypes.windll.user32.AllowSetForegroundWindow(-1)  # ASFW_ANY
    socket.write(b"show")
    socket.flush()
    socket.waitForBytesWritten(TIMEOUT_MS)
    socket.disconnectFromServer()
    return True


class SingleInstanceServer(QObject):
    def __init__(self, on_show: Callable[[], None], parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._on_show = on_show
        self._server = QLocalServer(self)
        # Clear a leftover channel from a copy that crashed or was force-killed.
        QLocalServer.removeServer(_channel_name())
        self._server.listen(_channel_name())
        self._server.newConnection.connect(self._on_connection)

    def _on_connection(self) -> None:
        socket = self._server.nextPendingConnection()
        if socket is None:
            return
        socket.readyRead.connect(lambda: self._on_message(socket))
        socket.disconnected.connect(socket.deleteLater)

    def _on_message(self, socket: QLocalSocket) -> None:
        if bytes(socket.readAll()).startswith(b"show"):
            self._on_show()