"""Launch Daylog when you sign in to Windows.

Windows starts every program listed under this registry key at sign-in:
    HKEY_CURRENT_USER\\Software\\Microsoft\\Windows\\CurrentVersion\\Run
It's per-user, needs no admin rights, and shows up in
Task Manager → Startup apps, where you can also turn it off.

We start with --minimized so Daylog goes straight to the tray.
"""

from __future__ import annotations

import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
VALUE_NAME = "Daylog"
MINIMIZED_FLAG = "--minimized"

if IS_WINDOWS:
    import winreg  # built into Python on Windows


def supported() -> bool:
    return IS_WINDOWS


def launch_command() -> str:
    """The command Windows runs at sign-in."""
    if getattr(sys, "frozen", False):
        # Packaged .exe (PyInstaller, a later step): just run it.
        return f'"{sys.executable}" {MINIMIZED_FLAG}'

    # Running from source: use pythonw.exe (no black console window)
    # from the same venv, and the absolute path to main.py.
    python = Path(sys.executable)
    pythonw = python.with_name("pythonw.exe")
    if pythonw.exists():
        python = pythonw
    main_py = Path(__file__).resolve().parent.parent / "main.py"
    return f'"{python}" "{main_py}" {MINIMIZED_FLAG}'


def _read() -> str | None:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            value, _type = winreg.QueryValueEx(key, VALUE_NAME)
            return str(value)
    except OSError:  # key or value doesn't exist
        return None


def is_enabled() -> bool:
    return IS_WINDOWS and _read() is not None


def set_enabled(enabled: bool) -> None:
    if not IS_WINDOWS:
        return
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if enabled:
            winreg.SetValueEx(key, VALUE_NAME, 0, winreg.REG_SZ, launch_command())
        else:
            try:
                winreg.DeleteValue(key, VALUE_NAME)
            except FileNotFoundError:
                pass


def refresh_if_enabled() -> None:
    """If you moved the project folder or venv, point the entry at the new location."""
    if is_enabled() and _read() != launch_command():
        set_enabled(True)


def started_minimized() -> bool:
    return MINIMIZED_FLAG in sys.argv