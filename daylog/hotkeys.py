"""System-wide keyboard shortcuts on Windows, with no extra packages.

How it works:
1. We ask Windows to reserve a key combo for us with RegisterHotKey (via ctypes).
2. When pressed anywhere, Windows posts a WM_HOTKEY message to our app.
3. Qt receives every raw Windows message first; our "native event filter"
   spots WM_HOTKEY and runs the matching Python callback.

No background threads or keyboard hooks, so it's light and antivirus-friendly.
On macOS/Linux this quietly does nothing (register() returns False).
"""

from __future__ import annotations

import ctypes
import sys
from typing import Callable

from PySide6.QtCore import QAbstractNativeEventFilter, QCoreApplication, QObject, QTimer

IS_WINDOWS = sys.platform == "win32"

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000  # holding the keys down fires once, not repeatedly

_MODIFIERS = {
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "alt": MOD_ALT,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
}

_NAMED_KEYS = {
    "space": 0x20,
    "enter": 0x0D,
    "tab": 0x09,
    "insert": 0x2D,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
}


def parse_hotkey(combo: str) -> tuple[int, int]:
    """'Ctrl+Alt+D' -> (modifier flags, Windows virtual-key code)."""
    parts = [p.strip().lower() for p in combo.split("+") if p.strip()]
    if len(parts) < 2:
        raise ValueError(f"{combo!r}: needs at least one modifier and a key")
    *modifier_names, key = parts

    modifiers = 0
    for name in modifier_names:
        if name not in _MODIFIERS:
            raise ValueError(f"{combo!r}: unknown modifier {name!r}")
        modifiers |= _MODIFIERS[name]

    return modifiers, _key_to_vk(key, combo)


def _key_to_vk(key: str, combo: str) -> int:
    if len(key) == 1 and key.isascii() and key.isalnum():
        return ord(key.upper())  # A-Z and 0-9 use their ASCII codes
    if key[0] == "f" and key[1:].isdigit() and 1 <= int(key[1:]) <= 24:
        return 0x70 + int(key[1:]) - 1  # F1 = 0x70
    if key in _NAMED_KEYS:
        return _NAMED_KEYS[key]
    raise ValueError(f"{combo!r}: unsupported key {key!r}")


if IS_WINDOWS:
    from ctypes import wintypes

    _user32 = ctypes.WinDLL("user32", use_last_error=True)
    _user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
    _user32.RegisterHotKey.restype = wintypes.BOOL
    _user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.UnregisterHotKey.restype = wintypes.BOOL


class _HotkeyFilter(QAbstractNativeEventFilter):
    """Sees every raw Windows message before Qt handles it."""

    def __init__(self, on_hotkey: Callable[[int], None]) -> None:
        super().__init__()
        self._on_hotkey = on_hotkey

    def nativeEventFilter(self, event_type, message):  # noqa: N802 (Qt's name)
        if bytes(event_type) == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self._on_hotkey(int(msg.wParam))  # wParam = our hotkey id
                return True, 0  # handled
        return False, 0  # let Qt handle everything else


class GlobalHotkeys(QObject):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._callbacks: dict[int, Callable[[], None]] = {}
        self._next_id = 1
        self._filter: _HotkeyFilter | None = None
        if IS_WINDOWS:
            self._filter = _HotkeyFilter(self._dispatch)
            QCoreApplication.instance().installNativeEventFilter(self._filter)

    @property
    def supported(self) -> bool:
        return IS_WINDOWS

    def register(self, combo: str, callback: Callable[[], None]) -> bool:
        """Returns False if unsupported here or another app already owns the combo."""
        if not IS_WINDOWS:
            return False
        modifiers, vk = parse_hotkey(combo)
        hotkey_id = self._next_id
        self._next_id += 1
        # hWnd=None: Windows sends WM_HOTKEY to this thread (Qt's GUI thread).
        if not _user32.RegisterHotKey(None, hotkey_id, modifiers | MOD_NOREPEAT, vk):
            return False
        self._callbacks[hotkey_id] = callback
        return True

    def unregister_all(self) -> None:
        if IS_WINDOWS:
            for hotkey_id in self._callbacks:
                _user32.UnregisterHotKey(None, hotkey_id)
        self._callbacks.clear()

    def _dispatch(self, hotkey_id: int) -> None:
        callback = self._callbacks.get(hotkey_id)
        if callback:
            # Run it right after the filter returns, not inside it, so
            # opening windows from the callback is safe.
            QTimer.singleShot(0, callback)