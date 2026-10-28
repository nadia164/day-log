
"""Input box + list of today's accomplishments.
Press Enter or click Add to log one."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .formatting import format_time
from .models import Accomplishment
from .qt_utils import clear_layout
from .store import TodayStore


class AccomplishmentsSection(QFrame):
    def __init__(self, store: TodayStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self._store = store

        title = QLabel("Accomplishments")
        title.setObjectName("cardTitle")

        self._input = QLineEdit()
        self._input.setPlaceholderText("What did you get done?")
        self._input.returnPressed.connect(self._submit)

        add_button = QPushButton("Add")
        add_button.setObjectName("addButton")
        add_button.setCursor(Qt.CursorShape.PointingHandCursor)
        add_button.clicked.connect(self._submit)

        input_row = QHBoxLayout()
        input_row.setSpacing(12)
        input_row.addWidget(self._input, 1)
        input_row.addWidget(add_button)

        self._empty_label = QLabel("Nothing logged yet. Small wins count too.")
        self._empty_label.setObjectName("muted")

        self._list = QVBoxLayout()
        self._list.setSpacing(4)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addLayout(input_row)
        layout.addSpacing(4)
        layout.addWidget(self._empty_label)
        layout.addLayout(self._list)

        store.accomplishments_changed.connect(self._refresh)
        self._refresh()

    def _submit(self) -> None:
        if self._store.add_accomplishment(self._input.text()):
            self._input.clear()
        self._input.setFocus()  # keep typing without clicking back in

    def _refresh(self) -> None:
        clear_layout(self._list)
        items = self._store.accomplishments
        self._empty_label.setVisible(not items)
        for item in items:
            self._list.addWidget(self._build_row(item))

    def _build_row(self, item: Accomplishment) -> QWidget:
        check = QLabel("✓")
        check.setObjectName("check")
        check.setAlignment(Qt.AlignmentFlag.AlignTop)

        text = QLabel(item.text)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        time = QLabel(format_time(item.created_at))
        time.setObjectName("muted")

        text_column = QVBoxLayout()
        text_column.setSpacing(0)
        text_column.addWidget(text)
        text_column.addWidget(time)

        delete = QToolButton()
        delete.setObjectName("deleteButton")
        delete.setText("✕")
        delete.setToolTip("Delete")
        delete.setCursor(Qt.CursorShape.PointingHandCursor)
        # Bind the id now; a plain lambda would capture the loop variable.
        delete.clicked.connect(
            lambda _=False, i=item.id: self._store.remove_accomplishment(i)
        )

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 6, 0, 6)
        row_layout.setSpacing(12)
        row_layout.addWidget(check)
        row_layout.addLayout(text_column, 1)
        row_layout.addWidget(delete, 0, Qt.AlignmentFlag.AlignTop)
        return row