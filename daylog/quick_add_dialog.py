"""Small always-on-top popup for logging an accomplishment without opening
the main window. Used by the tray now, and by the global hotkey next step."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .qt_utils import bring_to_front
from .store import TodayStore


class QuickAddDialog(QDialog):
    def __init__(self, store: TodayStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self.setObjectName("quickAdd")
        self.setWindowTitle("Add accomplishment")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.setMinimumWidth(440)

        title = QLabel("What did you get done?")
        title.setObjectName("cardTitle")

        self._input = QLineEdit()
        self._input.setPlaceholderText("e.g. Fixed the login bug")
        self._input.returnPressed.connect(self._submit)

        cancel = QPushButton("Cancel")
        cancel.setObjectName("secondaryButton")
        cancel.clicked.connect(self.reject)
        add = QPushButton("Add")
        add.setObjectName("addButton")
        add.clicked.connect(self._submit)

        buttons = QHBoxLayout()
        buttons.addStretch()
        buttons.addWidget(cancel)
        buttons.addWidget(add)

        hint = QLabel("Enter to save · Esc to close")
        hint.setObjectName("muted")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(self._input)
        layout.addWidget(hint)
        layout.addLayout(buttons)

    def open_fresh(self) -> None:
        """Show an empty popup, in front of everything, ready to type."""
        self._input.clear()
        bring_to_front(self)
        self._input.setFocus()

    def _submit(self) -> None:
        # Always logs to *today*, whatever day the main window is showing.
        if self._store.add_accomplishment(self._input.text(), day=date.today()):
            self.accept()
        else:
            self._input.setFocus()