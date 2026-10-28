"""Daylog: personal Time In / Time Out with per-day accomplishments.

Run with:  python main.py   (or the installed Daylog.exe)
Stop with: Quit Daylog in the tray menu, or Ctrl+C in the terminal.
"""

import signal
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtWidgets import QApplication, QSystemTrayIcon

from daylog import __version__, startup
from daylog.config import (
    END_OF_DAY_REMINDER,
    IDLE_MINUTES,
    QUICK_ADD_HOTKEY,
    SNOOZE_MINUTES,
    TOGGLE_CLOCK_HOTKEY,
)
from daylog.hotkeys import GlobalHotkeys
from daylog.icons import make_app_icon
from daylog.idle import IdleMonitor
from daylog.idle_dialog import IdleDialog, format_away
from daylog.main_window import MainWindow
from daylog.reminder import EndOfDayReminder, ReminderDialog, parse_time
from daylog.reports_window import ReportsWindow
from daylog.single_instance import (
    SingleInstanceServer,
    hold_app_mutex,
    notify_running_instance,
)
from daylog.store import TodayStore
from daylog.theme import STYLESHEET
from daylog.tray import TrayController


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Daylog")  # also names the AppData folder
    app.setApplicationVersion(__version__)
    app.setStyle("Fusion")  # same look on every Windows version
    app.setStyleSheet(STYLESHEET)
    app.setWindowIcon(make_app_icon())
    install_error_log()

    # Already running (e.g. in the tray)? Ask that copy to show its window and stop here.
    if notify_running_instance():
        sys.exit(0)
    hold_app_mutex()  # lets the installer detect that Daylog is running

    # Ctrl+C in the terminal: Qt's event loop runs in C++, so Python never gets
    # a chance to notice the keypress. A do-nothing timer hands control back to
    # Python every 200 ms, which lets the handler run.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    heartbeat = QTimer()
    heartbeat.timeout.connect(lambda: None)
    heartbeat.start(200)

    # One store for the whole app. The window, tray, hotkeys and idle monitor
    # all call the same store methods.
    store = TodayStore()
    app.aboutToQuit.connect(store.close)

    window = MainWindow(store)
    window.resize(560, 760)
    # Listen for later launches asking us to show the window.
    SingleInstanceServer(window.show_and_raise, parent=app)

    reports = ReportsWindow(store)
    reports.resize(760, 860)
    window.reports_requested.connect(reports.open)
    reports.home_requested.connect(window.show_and_raise)

    tray = None
    hotkeys = GlobalHotkeys(app)
    app.aboutToQuit.connect(hotkeys.unregister_all)

    if QSystemTrayIcon.isSystemTrayAvailable():
        # Keep running when the window is closed; quit from the tray menu.
        app.setQuitOnLastWindowClosed(False)
        window.close_to_tray = True
        tray = TrayController(store, window)
        tray.show()
        # Remove the icon explicitly on quit (Ctrl+C or Quit Daylog), instead of
        # relying on cleanup order, so no "ghost" icon is left behind.
        app.aboutToQuit.connect(tray.hide)
        setup_hotkeys(hotkeys, tray)

    # Keep references so Python doesn't garbage-collect them.
    idle = setup_idle(app, store, tray)  # noqa: F841
    reminder = setup_reminder(app, store, tray)  # noqa: F841

    if startup.supported():
        startup.refresh_if_enabled()

    # Launched at sign-in (--minimized): stay in the tray. Otherwise show the window.
    if not (tray and startup.started_minimized()):
        window.show()
    sys.exit(app.exec())


def install_error_log() -> None:
    """The packaged app has no console, so errors would vanish silently.
    Write them to AppData\\Roaming\\Daylog\\error.log instead (and still
    print them when a console exists)."""
    folder = Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation))
    log_path = folder / "error.log"

    def log_error(exc_type, exc, tb) -> None:
        text = "".join(traceback.format_exception(exc_type, exc, tb))
        try:
            folder.mkdir(parents=True, exist_ok=True)
            with log_path.open("a", encoding="utf-8") as log:
                log.write(f"\n=== {datetime.now():%Y-%m-%d %H:%M:%S} · Daylog {__version__} ===\n{text}")
        except OSError:
            pass
        if sys.stderr:
            sys.stderr.write(text)

    sys.excepthook = log_error


def setup_hotkeys(hotkeys: GlobalHotkeys, tray: TrayController) -> None:
    if not hotkeys.supported:
        return
    shortcuts = {
        QUICK_ADD_HOTKEY: tray.quick_add.open_fresh,
        TOGGLE_CLOCK_HOTKEY: tray.on_toggle_clock_hotkey,
    }
    taken = [combo for combo, action in shortcuts.items() if not hotkeys.register(combo, action)]

    tray.set_shortcut_hints(
        toggle_clock="" if TOGGLE_CLOCK_HOTKEY in taken else TOGGLE_CLOCK_HOTKEY,
        quick_add="" if QUICK_ADD_HOTKEY in taken else QUICK_ADD_HOTKEY,
    )
    if taken:
        tray.notify(
            "Shortcut unavailable",
            f"{', '.join(taken)} is already used by another app. "
            "Change it in daylog/config.py.",
        )


def setup_idle(app: QApplication, store: TodayStore, tray: TrayController | None):
    if IDLE_MINUTES <= 0:
        return None
    monitor = IdleMonitor(store, timedelta(minutes=IDLE_MINUTES), parent=app)
    if not monitor.supported:
        return None
    dialog = IdleDialog(store)

    def on_returned(session_id, away_since, back_at) -> None:
        monitor.pause()  # don't stack up dialogs while this one is open
        dialog.ask(session_id, away_since, back_at)

    def on_time_removed(removed: timedelta, still_clocked_in: bool) -> None:
        if tray is None:
            return
        detail = "Still clocked in." if still_clocked_in else "You're clocked out."
        tray.notify(f"Removed {format_away(removed)} of away time", detail,
                    kind="on" if still_clocked_in else "off")

    monitor.returned.connect(on_returned)
    dialog.finished.connect(lambda _result: monitor.resume())
    dialog.time_removed.connect(on_time_removed)
    monitor.start()
    return monitor, dialog


def setup_reminder(app: QApplication, store: TodayStore, tray: TrayController | None):
    if not END_OF_DAY_REMINDER:
        return None
    reminder = EndOfDayReminder(
        store, parse_time(END_OF_DAY_REMINDER), timedelta(minutes=SNOOZE_MINUTES), parent=app
    )
    dialog = ReminderDialog(store, SNOOZE_MINUTES)

    def on_time_out() -> None:
        reminder.done_for_today()
        if not store.is_clocked_in:
            return
        if tray:
            tray.toggle_clock_with_feedback()  # clocks out + shows the corner popup
        else:
            store.time_out()

    reminder.due.connect(dialog.show_reminder)
    dialog.time_out_chosen.connect(on_time_out)
    dialog.snooze_chosen.connect(reminder.snoozed)
    dialog.keep_working_chosen.connect(reminder.done_for_today)
    reminder.start()
    return reminder, dialog


if __name__ == "__main__":
    main()