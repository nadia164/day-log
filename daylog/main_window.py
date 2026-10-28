"""The main window: a date header with day navigation, the clock card,
and accomplishments."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .accomplishments_section import AccomplishmentsSection
from .formatting import format_date
from .qt_utils import bring_to_front
from .session_card import SessionCard
from .store import TodayStore


class MainWindow(QMainWindow):
    # Emitted when the X button hides the window instead of quitting.
    hidden_to_tray = Signal()
    # Emitted by the Reports button / Ctrl+R; main.py opens the Reports window.
    reports_requested = Signal()

    def __init__(self, store: TodayStore) -> None:
        super().__init__()
        self._store = store
        # main.py turns this on when a system tray is available.
        self.close_to_tray = False
        self.setWindowTitle("Daylog")
        self.setMinimumSize(420, 520)

        # ---- header: date + ‹ Today › ----
        self._date_label = QLabel()
        self._date_label.setObjectName("dateLabel")
        self._date_label.setWordWrap(True)

        self._prev_button = _nav_button("‹", "Previous day (Alt+Left)")
        self._prev_button.clicked.connect(store.previous_day)
        self._next_button = _nav_button("›", "Next day (Alt+Right)")
        self._next_button.clicked.connect(store.next_day)

        self._today_button = QPushButton("Today")
        self._today_button.setObjectName("todayButton")
        self._today_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._today_button.clicked.connect(store.go_to_today)

        reports_button = QPushButton("Reports")
        reports_button.setObjectName("reportsButton")
        reports_button.setToolTip("Weekly and monthly reports (Ctrl+R)")
        reports_button.setCursor(Qt.CursorShape.PointingHandCursor)
        reports_button.clicked.connect(self.reports_requested)

        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(self._date_label, 1)
        header.addWidget(reports_button)
        header.addSpacing(4)
        header.addWidget(self._today_button)
        header.addWidget(self._prev_button)
        header.addWidget(self._next_button)

        # Keyboard shortcuts (while this window is focused).
        QShortcut(QKeySequence("Alt+Left"), self, store.previous_day)
        QShortcut(QKeySequence("Alt+Right"), self, store.next_day)
        QShortcut(QKeySequence("Ctrl+R"), self, self.reports_requested.emit)

        # ---- content column, capped at 720px so it stays readable maximized ----
        column = QWidget()
        column.setMaximumWidth(720)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(24, 24, 24, 24)
        column_layout.setSpacing(16)
        column_layout.addLayout(header)
        column_layout.addWidget(SessionCard(store))
        column_layout.addWidget(AccomplishmentsSection(store))
        column_layout.addStretch()

        # Center the column horizontally.
        page = QWidget()
        page.setObjectName("page")
        page.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        page_layout = QHBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.addStretch(1)
        page_layout.addWidget(column, 100)
        page_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(page)
        self.setCentralWidget(scroll)

        store.day_changed.connect(self._refresh_header)
        self._refresh_header()

    def show_and_raise(self) -> None:
        """Bring the window back from the tray (or from minimized) to the front."""
        if self.isMinimized():
            self.showNormal()
        bring_to_front(self)

    def closeEvent(self, event: QCloseEvent) -> None:
        # Clicking X hides to the tray. Quitting happens from the tray menu.
        if self.close_to_tray:
            event.ignore()
            self.hide()
            self.hidden_to_tray.emit()
        else:
            super().closeEvent(event)

    def _refresh_header(self) -> None:
        self._date_label.setText(format_date(self._store.day))
        self._next_button.setEnabled(not self._store.is_today)
        self._today_button.setVisible(not self._store.is_today)


def _nav_button(text: str, tooltip: str) -> QToolButton:
    button = QToolButton()
    button.setObjectName("navButton")
    button.setText(text)
    button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button