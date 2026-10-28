"""System tray icon: quick Time In/Out, quick-add, live status in the tooltip."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import startup
from .config import CONFIRM_CLOCK_HOTKEY
from .confirm_clock_dialog import ConfirmClockDialog
from .formatting import format_duration, format_time
from .icons import make_tray_icon
from .main_window import MainWindow
from .quick_add_dialog import QuickAddDialog
from .store import TodayStore
from .toast import Toast


class TrayController(QObject):
    def __init__(
        self, store: TodayStore, window: MainWindow, parent: QObject | None = None
    ) -> None:
        super().__init__(parent)
        self._store = store
        self._window = window
        self._hint_shown = False
        self._icon_idle = make_tray_icon(clocked_in=False)
        self._icon_active = make_tray_icon(clocked_in=True)

        self.quick_add = QuickAddDialog(store)
        self.toast = Toast()
        self.confirm_clock = ConfirmClockDialog(store, on_confirmed=self.toggle_clock_with_feedback)

        # ---- menu (right-click) ----
        self._menu = QMenu()
        self._status_action = self._menu.addAction("")
        self._status_action.setEnabled(False)  # just a label
        self._menu.addSeparator()

        self._clock_action = self._menu.addAction("")
        self._clock_action.triggered.connect(self._toggle_clock)
        self._add_action = self._menu.addAction("Add accomplishment…")
        self._add_action.triggered.connect(self.quick_add.open_fresh)
        reports_action = self._menu.addAction("Reports…")
        reports_action.triggered.connect(window.reports_requested)
        # Filled in by set_shortcut_hints() once hotkeys are registered.
        self._clock_hint = ""
        self._add_hint = ""
        self._menu.addSeparator()

        if startup.supported():
            self._startup_action = self._menu.addAction("Launch at startup")
            self._startup_action.setCheckable(True)
            self._startup_action.setChecked(startup.is_enabled())
            self._startup_action.toggled.connect(self._on_startup_toggled)
            self._menu.addSeparator()

        open_action = self._menu.addAction("Open Daylog")
        open_action.triggered.connect(window.show_and_raise)
        font = open_action.font()
        font.setBold(True)
        open_action.setFont(font)
        quit_action = self._menu.addAction("Quit Daylog")
        quit_action.triggered.connect(QApplication.quit)

        self._menu.aboutToShow.connect(self._refresh)

        # ---- tray icon ----
        self._tray = QSystemTrayIcon(self._icon_idle, self)
        self._tray.setContextMenu(self._menu)
        self._tray.activated.connect(self._on_activated)

        # Keep in sync with the app.
        store.sessions_changed.connect(self._refresh)
        window.hidden_to_tray.connect(self._on_window_hidden)

        # Live timer in the tooltip while clocked in.
        self._ticker = QTimer(self)
        self._ticker.setInterval(1000)
        self._ticker.timeout.connect(self._on_tick)
        self._ticker.start()

        self._refresh()

    def show(self) -> None:
        self._tray.show()

    def hide(self) -> None:
        """Remove the icon from the tray right away (called when quitting)."""
        self.toast.hide()
        self._tray.hide()

    def notify(self, title: str, text: str, kind: str = "info", duration_ms: int = 3000) -> None:
        """Daylog's own popup in the bottom-right corner (see toast.py)."""
        self.toast.show_message(title, text, kind, duration_ms)

    def set_shortcut_hints(self, toggle_clock: str = "", quick_add: str = "") -> None:
        """Show hotkeys on the right side of menu items (the tab separates them)."""
        self._clock_hint = toggle_clock
        self._add_hint = quick_add
        self._add_action.setText(_with_hint("Add accomplishment…", quick_add))
        self._refresh()

    def on_toggle_clock_hotkey(self) -> None:
        """Ctrl+Alt+T: ask first (see config.CONFIRM_CLOCK_HOTKEY), then toggle."""
        if CONFIRM_CLOCK_HOTKEY:
            self.confirm_clock.ask()
        else:
            self.toggle_clock_with_feedback()

    def toggle_clock_with_feedback(self) -> None:
        """For the hotkey: no window is visible, so confirm with a notification."""
        self._toggle_clock()
        active = self._store.active_session
        if active:
            self.notify("Clocked in", f"Started at {format_time(active.start)}", kind="on")
        else:
            total = format_duration(self._store.today_total(datetime.now()))
            self.notify("Clocked out", f"{total} worked today", kind="off")

    # ---- events --------------------------------------------------------

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        # Left-click opens the window; right-click shows the menu automatically.
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self._window.show_and_raise()

    def _on_startup_toggled(self, enabled: bool) -> None:
        try:
            startup.set_enabled(enabled)
        except OSError as error:
            self._startup_action.blockSignals(True)
            self._startup_action.setChecked(not enabled)
            self._startup_action.blockSignals(False)
            self.notify("Couldn't change startup setting", str(error))
            return
        if enabled:
            self.notify("Launch at startup is on", "Daylog will start in the tray when you sign in.", kind="on")
        else:
            self.notify("Launch at startup is off", "", kind="off")

    def _toggle_clock(self) -> None:
        if self._store.is_clocked_in:
            self._store.time_out()
        else:
            self._store.time_in()

    def _on_window_hidden(self) -> None:
        # Tell the user once per run that the app didn't actually quit.
        if not self._hint_shown:
            self._hint_shown = True
            self.notify(
                "Daylog is still running",
                "Use the tray icon to Time In/Out or reopen the window. "
                "Right-click → Quit to exit.",
                duration_ms=5000,
            )

    def _on_tick(self) -> None:
        if self._store.is_clocked_in:
            self._refresh_text()

    # ---- drawing -------------------------------------------------------

    def _refresh(self) -> None:
        clocked_in = self._store.is_clocked_in
        self._tray.setIcon(self._icon_active if clocked_in else self._icon_idle)
        self._clock_action.setText(
            _with_hint("Time Out" if clocked_in else "Time In", self._clock_hint)
        )
        self._refresh_text()

    def _refresh_text(self) -> None:
        status = self.status_text()
        self._status_action.setText(status)
        self._tray.setToolTip(f"Daylog\n{status}")

    def status_text(self) -> str:
        total = format_duration(self._store.today_total(datetime.now()))
        state = "Clocked in" if self._store.is_clocked_in else "Not clocked in"
        return f"{state} · {total} today"


def _with_hint(label: str, hint: str) -> str:
    return f"{label}\t{hint}" if hint else label