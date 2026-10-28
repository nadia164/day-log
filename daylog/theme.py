"""App-wide stylesheet (Qt's version of CSS). Widgets opt in via setObjectName()."""

STYLESHEET = """
QWidget {
    font-family: "Segoe UI";
    font-size: 10pt;
    color: #1f2333;
}

QMainWindow, QScrollArea, QWidget#page {
    background: #f5f6fa;
    border: none;
}

/* ---- cards ---- */
QFrame#card {
    background: #ffffff;
    border: 1px solid #e4e6ef;
    border-radius: 12px;
}
QFrame#divider {
    background: #e4e6ef;
    border: none;
}

/* ---- text ---- */
QLabel#dateLabel   { font-size: 16pt; font-weight: 600; }
QLabel#cardTitle   { font-size: 12pt; font-weight: 600; }
QLabel#sectionTitle { font-weight: 600; }
QLabel#caption, QLabel#muted { color: #6b7085; }
QLabel#timer       { font-size: 30pt; font-weight: 600; }
QLabel#check       { color: #4f46e5; font-size: 13pt; font-weight: 700; }

QLabel#statusDot {
    background: #c3c6d4;
    border-radius: 5px;
}
QLabel#statusDot[active="true"] { background: #22a55b; }

/* ---- buttons ---- */
QPushButton#clockButton, QPushButton#addButton {
    background: #4f46e5;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}
QPushButton#clockButton:hover, QPushButton#addButton:hover { background: #4338ca; }
QPushButton#clockButton:pressed, QPushButton#addButton:pressed { background: #3730a3; }

/* Time Out uses a softer style so it doesn't look like the same action */
QPushButton#clockButton[clockedIn="true"]         { background: #e0e7ff; color: #3730a3; }
QPushButton#clockButton[clockedIn="true"]:hover   { background: #c7d2fe; }
QPushButton#clockButton[clockedIn="true"]:pressed { background: #a5b4fc; }

/* ---- day navigation ---- */
QToolButton#navButton {
    background: #ffffff;
    border: 1px solid #cfd3e0;
    border-radius: 8px;
    padding: 2px 10px;
    font-size: 14pt;
    color: #3730a3;
}
QToolButton#navButton:hover    { background: #eef0fb; }
QToolButton#navButton:disabled { color: #c3c6d4; border-color: #e4e6ef; }

QPushButton#todayButton {
    background: #e0e7ff;
    color: #3730a3;
    border: none;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}
QPushButton#todayButton:hover { background: #c7d2fe; }

QToolButton#deleteButton {
    background: transparent;
    border: none;
    border-radius: 6px;
    color: #8a8fa3;
    padding: 4px 8px;
}
QToolButton#deleteButton:hover { background: #fde8e8; color: #c62828; }

QPushButton#secondaryButton {
    background: transparent;
    color: #3730a3;
    border: 1px solid #cfd3e0;
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 600;
}
QPushButton#secondaryButton:hover { background: #eef0fb; }

/* ---- quick-add popup ---- */
QDialog#quickAdd { background: #f5f6fa; }

/* ---- reports ---- */
QLabel#statValue { font-size: 17pt; font-weight: 600; }

QPushButton#segment {
    background: #ffffff;
    color: #3730a3;
    border: 1px solid #cfd3e0;
    padding: 7px 16px;
    font-weight: 600;
}
QPushButton#segment[position="left"]  { border-top-left-radius: 8px;  border-bottom-left-radius: 8px; border-right: none; }
QPushButton#segment[position="right"] { border-top-right-radius: 8px; border-bottom-right-radius: 8px; }
QPushButton#segment:hover        { background: #eef0fb; }
QPushButton#segment:checked      { background: #4f46e5; color: #ffffff; border-color: #4f46e5; }

QToolButton#exportButton, QPushButton#reportsButton {
    background: #ffffff;
    color: #3730a3;
    border: 1px solid #cfd3e0;
    border-radius: 8px;
    padding: 7px 14px;
    font-weight: 600;
}
QToolButton#exportButton:hover, QPushButton#reportsButton:hover { background: #eef0fb; }
QToolButton#exportButton::menu-indicator { image: none; }

QToolTip {
    background: #1f2333;
    color: #ffffff;
    border: none;
    padding: 6px 8px;
}

/* ---- toast popup ---- */
QFrame#toast {
    background: #1f2333;
    border-radius: 12px;
}
QLabel#toastTitle   { color: #ffffff; font-weight: 600; font-size: 11pt; }
QLabel#toastMessage { color: #c3c6d4; }
QLabel#toastDot                 { background: #818cf8; border-radius: 5px; }
QLabel#toastDot[kind="on"]      { background: #22c55e; }
QLabel#toastDot[kind="off"]     { background: #8a8fa3; }

/* ---- tray menu ---- */
QMenu {
    background: #ffffff;
    border: 1px solid #e4e6ef;
    border-radius: 8px;
    padding: 6px;
}
QMenu::item {
    padding: 7px 28px 7px 12px;
    border-radius: 6px;
}
QMenu::item:selected { background: #eef0fb; color: #1f2333; }
QMenu::item:disabled { color: #6b7085; }
QMenu::separator {
    height: 1px;
    background: #e4e6ef;
    margin: 4px 8px;
}

/* ---- input ---- */
QLineEdit {
    background: #ffffff;
    border: 1px solid #cfd3e0;
    border-radius: 8px;
    padding: 9px 12px;
}
QLineEdit:focus { border: 1px solid #4f46e5; }
"""