"""Reports: week or month totals, hours-per-day chart, accomplishments by day,
and CSV / Markdown export."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QButtonGroup,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .bar_chart import Bar, BarChart
from .export import to_csv, to_markdown
from .formatting import format_hours, format_range, format_short_date
from .qt_utils import bring_to_front, clear_layout
from .reports import Report, month_range, week_range
from .store import TodayStore

WEEK, MONTH = "week", "month"


class ReportsWindow(QWidget):
    # "← Home" was clicked; main.py brings the main window to the front.
    home_requested = Signal()

    def __init__(self, store: TodayStore, parent: QWidget | None = None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self._store = store
        self._mode = WEEK
        self._anchor = date.today()  # any day inside the period on screen
        self._report: Report | None = None

        self.setWindowTitle("Daylog Reports")
        self.setMinimumSize(560, 560)
        self.resize(760, 860)

        # ---- header ----
        home_button = QPushButton("← Home")
        home_button.setObjectName("reportsButton")  # same outlined style
        home_button.setToolTip("Back to the main window (Ctrl+W closes Reports)")
        home_button.setCursor(Qt.CursorShape.PointingHandCursor)
        home_button.clicked.connect(self._go_home)

        title = QLabel("Reports")
        title.setObjectName("dateLabel")

        self._week_button = _segment("Week", "left")
        self._month_button = _segment("Month", "right")
        self._week_button.setChecked(True)
        group = QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(self._week_button)
        group.addButton(self._month_button)
        self._week_button.clicked.connect(lambda: self._set_mode(WEEK))
        self._month_button.clicked.connect(lambda: self._set_mode(MONTH))

        segments = QHBoxLayout()
        segments.setSpacing(0)
        segments.addWidget(self._week_button)
        segments.addWidget(self._month_button)

        self._export_button = QToolButton()
        self._export_button.setObjectName("exportButton")
        self._export_button.setText("Export")
        self._export_button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self._export_button.setCursor(Qt.CursorShape.PointingHandCursor)
        menu = QMenu(self._export_button)
        menu.addAction("Save as CSV…", self._export_csv)
        menu.addAction("Save as Markdown…", self._export_markdown)
        menu.addSeparator()
        menu.addAction("Copy as Markdown", self._copy_markdown)
        self._export_button.setMenu(menu)

        top_row = QHBoxLayout()
        top_row.addWidget(home_button)
        top_row.addSpacing(8)
        top_row.addWidget(title)
        top_row.addStretch()
        top_row.addLayout(segments)
        top_row.addSpacing(8)
        top_row.addWidget(self._export_button)

        self._period_label = QLabel()
        self._period_label.setObjectName("cardTitle")
        self._current_button = QPushButton()
        self._current_button.setObjectName("todayButton")
        self._current_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self._current_button.clicked.connect(self._go_current)
        self._prev_button = _nav_button("‹", "Previous (Alt+Left)")
        self._prev_button.clicked.connect(lambda: self._step(-1))
        self._next_button = _nav_button("›", "Next (Alt+Right)")
        self._next_button.clicked.connect(lambda: self._step(1))

        period_row = QHBoxLayout()
        period_row.setSpacing(8)
        period_row.addWidget(self._period_label, 1)
        period_row.addWidget(self._current_button)
        period_row.addWidget(self._prev_button)
        period_row.addWidget(self._next_button)

        self._status = QLabel()
        self._status.setObjectName("muted")
        self._status.setVisible(False)
        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(lambda: self._status.setVisible(False))

        # ---- stat tiles ----
        self._tile_total = _StatTile("Total time")
        self._tile_days = _StatTile("Days worked")
        self._tile_average = _StatTile("Daily average")
        self._tile_items = _StatTile("Accomplishments")
        tiles = QHBoxLayout()
        tiles.setSpacing(12)
        for tile in (self._tile_total, self._tile_days, self._tile_average, self._tile_items):
            tiles.addWidget(tile, 1)

        # ---- chart card ----
        chart_card = _card()
        chart_title = QLabel("Hours per day")
        chart_title.setObjectName("cardTitle")
        self._chart = BarChart()
        chart_layout = chart_card.layout()
        chart_layout.addWidget(chart_title)
        chart_layout.addWidget(self._chart)

        # ---- accomplishments card ----
        items_card = _card()
        items_title = QLabel("Accomplishments")
        items_title.setObjectName("cardTitle")
        self._items_list = QVBoxLayout()
        self._items_list.setSpacing(14)
        items_card.layout().addWidget(items_title)
        items_card.layout().addLayout(self._items_list)

        # ---- page ----
        column = QWidget()
        column.setMaximumWidth(860)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(24, 24, 24, 24)
        column_layout.setSpacing(16)
        column_layout.addLayout(top_row)
        column_layout.addLayout(period_row)
        column_layout.addWidget(self._status)
        column_layout.addLayout(tiles)
        column_layout.addWidget(chart_card)
        column_layout.addWidget(items_card)
        column_layout.addStretch()

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
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

        QShortcut(QKeySequence("Alt+Left"), self, lambda: self._step(-1))
        QShortcut(QKeySequence("Alt+Right"), self, lambda: self._step(1))
        QShortcut(QKeySequence("Ctrl+W"), self, self.close)

        # Stay up to date: any saved change, plus a slow tick while clocked in.
        store.data_changed.connect(self.refresh)
        self._ticker = QTimer(self)
        self._ticker.setInterval(30_000)
        self._ticker.timeout.connect(self._on_tick)
        self._ticker.start()

    # ---- opening -------------------------------------------------------

    def open(self) -> None:
        self.refresh(force=True)
        bring_to_front(self)

    def _go_home(self) -> None:
        self.close()
        self.home_requested.emit()

    # ---- period --------------------------------------------------------

    def _range(self) -> tuple[date, date]:
        return week_range(self._anchor) if self._mode == WEEK else month_range(self._anchor)

    def _set_mode(self, mode: str) -> None:
        self._mode = mode  # keeps the same anchor day, so Week -> Month shows that week's month
        self.refresh()

    def _step(self, direction: int) -> None:
        start, end = self._range()
        if direction > 0 and end >= date.today():
            return  # no future periods
        if self._mode == WEEK:
            self._anchor = start + timedelta(days=7 * direction)
        else:
            # Day 1 of the previous / next month
            self._anchor = (start - timedelta(days=1)).replace(day=1) if direction < 0 else end + timedelta(days=1)
        self.refresh()

    def _go_current(self) -> None:
        self._anchor = date.today()
        self.refresh()

    def _on_tick(self) -> None:
        if self.isVisible() and self._store.is_clocked_in:
            self.refresh()

    # ---- drawing -------------------------------------------------------

    def refresh(self, force: bool = False) -> None:
        if not force and not self.isVisible():
            return  # hidden: skip the work, open() redraws
        start, end = self._range()
        report = self._store.report(start, end)
        self._report = report
        today = date.today()
        is_current = start <= today <= end

        self._period_label.setText(format_range(start, end))
        self._current_button.setText("This week" if self._mode == WEEK else "This month")
        self._current_button.setVisible(not is_current)
        self._next_button.setEnabled(not is_current)

        self._tile_total.set_value(format_hours(report.total))
        self._tile_days.set_value(str(report.days_worked))
        self._tile_average.set_value(format_hours(report.daily_average))
        self._tile_items.set_value(str(report.accomplishment_count))

        self._chart.set_bars([self._bar_for(d, i) for i, d in enumerate(report.days)])
        self._fill_accomplishments(report)

    def _bar_for(self, day_report, index: int) -> Bar:
        d = day_report.day
        if self._mode == WEEK:
            label = f"{d:%a}"
        else:
            # Month: label day 1 and every 5th day, plus today
            show = d.day == 1 or d.day % 5 == 0 or d == date.today()
            label = str(d.day) if show else ""
        return Bar(
            label=label,
            tooltip=f"{d:%a}, {format_short_date(d)}\n{format_hours(day_report.worked)}"
            f" · {len(day_report.accomplishments)} accomplishment"
            f"{'' if len(day_report.accomplishments) == 1 else 's'}",
            hours=None if day_report.is_future else day_report.worked.total_seconds() / 3600,
            emphasize_label=d == date.today(),
        )

    def _fill_accomplishments(self, report: Report) -> None:
        clear_layout(self._items_list)
        days = [d for d in report.days if d.accomplishments]
        if not days:
            empty = QLabel("No accomplishments logged in this period.")
            empty.setObjectName("muted")
            self._items_list.addWidget(empty)
            return
        for d in reversed(days):  # newest first
            block = QWidget()
            block_layout = QVBoxLayout(block)
            block_layout.setContentsMargins(0, 0, 0, 0)
            block_layout.setSpacing(4)
            header = QLabel(f"{d.day:%A}, {format_short_date(d.day)}  ·  {format_hours(d.worked)}")
            header.setObjectName("sectionTitle")
            block_layout.addWidget(header)
            for item in d.accomplishments:
                row = QLabel(f"✓  {item.text}")
                row.setWordWrap(True)
                row.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                block_layout.addWidget(row)
            self._items_list.addWidget(block)

    # ---- export --------------------------------------------------------

    def _file_stem(self) -> str:
        start, end = self._range()
        return f"daylog-{start.isoformat()}-to-{end.isoformat()}"

    def _save(self, text: str, extension: str, file_filter: str, encoding: str) -> None:
        folder = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation)
        path, _ = QFileDialog.getSaveFileName(
            self, "Save report", str(Path(folder) / f"{self._file_stem()}.{extension}"), file_filter
        )
        if not path:
            return
        try:
            # newline="" keeps the CSV module's line endings as they are
            Path(path).write_text(text, encoding=encoding, newline="")
        except OSError as error:
            self._show_status(f"Couldn't save: {error}")
            return
        self._show_status(f"Saved {Path(path).name}")

    def _export_csv(self) -> None:
        if self._report:
            # utf-8-sig adds a marker so Excel reads accents/emoji correctly
            self._save(to_csv(self._report), "csv", "CSV files (*.csv)", "utf-8-sig")

    def _export_markdown(self) -> None:
        if self._report:
            self._save(to_markdown(self._report), "md", "Markdown files (*.md)", "utf-8")

    def _copy_markdown(self) -> None:
        if self._report:
            QGuiApplication.clipboard().setText(to_markdown(self._report))
            self._show_status("Copied the report as Markdown. Paste it anywhere.")

    def _show_status(self, text: str) -> None:
        self._status.setText(text)
        self._status.setVisible(True)
        self._status_timer.start(5000)


class _StatTile(QFrame):
    def __init__(self, label: str) -> None:
        super().__init__()
        self.setObjectName("card")
        caption = QLabel(label)
        caption.setObjectName("caption")
        self._value = QLabel("–")
        self._value.setObjectName("statValue")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(2)
        layout.addWidget(caption)
        layout.addWidget(self._value)

    def set_value(self, text: str) -> None:
        self._value.setText(text)


def _card() -> QFrame:
    card = QFrame()
    card.setObjectName("card")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(24, 20, 24, 20)
    layout.setSpacing(12)
    return card


def _segment(text: str, position: str) -> QPushButton:
    button = QPushButton(text)
    button.setObjectName("segment")
    button.setProperty("position", position)  # for the rounded outer corners
    button.setCheckable(True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def _nav_button(text: str, tooltip: str) -> QToolButton:
    button = QToolButton()
    button.setObjectName("navButton")
    button.setText(text)
    button.setToolTip(tooltip)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button