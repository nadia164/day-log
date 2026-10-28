"""Tiny Qt helpers shared by the widgets."""

import sys

from PySide6.QtWidgets import QLayout, QWidget


def bring_to_front(widget: QWidget) -> None:
    """Show a window in front of whatever app you're in (e.g. from a hotkey).
    activateWindow() alone sometimes only flashes the taskbar on Windows."""
    widget.show()
    widget.raise_()
    widget.activateWindow()
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.user32.SetForegroundWindow(int(widget.winId()))


def clear_layout(layout: QLayout) -> None:
    """Remove and delete every widget in a layout (used before rebuilding lists)."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def repolish(widget: QWidget) -> None:
    """Re-apply the stylesheet after changing a property used in a selector,
    e.g. QPushButton[clockedIn="true"]."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)