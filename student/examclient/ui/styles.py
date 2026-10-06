EXAM_QSS = """
QWidget {
    font-family: 'Segoe UI', Arial;
    font-size: 15px;
    color: #e6e6e6;
}
QMainWindow, QStackedWidget, QWidget#page, QWidget#contentPane {
    background-color: #252526;
}
QFrame#card {
    background-color: #2d2d30;
    border: 1px solid #3f3f46;
    border-radius: 8px;
}
QFrame#topBar {
    background-color: #1f3763;
    border: none;
}
QWidget#navPane {
    background-color: #2d2d30;
    border: 1px solid #3f3f46;
    border-radius: 6px;
}
QScrollArea#navScroll, QWidget#navContainer {
    background-color: transparent;
    border: none;
}
QLabel#appTitle { font-size: 22px; font-weight: 700; color: #ffffff; }
QLabel#muted { color: #9aa0a6; font-size: 13px; }
QLabel#answeredCounter { color: #9aa0a6; font-size: 13px; padding: 4px 6px; }
QLabel#timer { font-size: 22px; font-weight: 700; color: #ffffff; }
QLabel#timerWarn {
    font-size: 22px; font-weight: 700;
    color: #ffffff; background-color: #7a2e2e;
    padding: 2px 10px; border-radius: 4px;
}
QLabel#statusBar { color: #b8c2d9; font-size: 13px; }
QLineEdit, QComboBox {
    background-color: #1e1e1e;
    border: 1px solid #4a4a4f;
    border-radius: 4px;
    padding: 8px 10px;
    color: #e6e6e6;
    selection-background-color: #3e6db0;
    selection-color: #ffffff;
}
QLineEdit:focus, QComboBox:focus { border-color: #7aa7e0; }
QComboBox QAbstractItemView {
    background-color: #1e1e1e;
    color: #e6e6e6;
    border: 1px solid #4a4a4f;
    selection-background-color: #3e6db0;
    selection-color: #ffffff;
}
QPushButton {
    background-color: #3e6db0;
    color: #ffffff;
    border: 1px solid #3e6db0;
    border-radius: 4px;
    padding: 9px 18px;
    font-weight: 600;
}
QPushButton:hover { background-color: #4f7ec2; }
QPushButton:disabled { background-color: #3a3a3f; border-color: #3a3a3f; color: #777777; }
QPushButton#secondary {
    background-color: #333336;
    color: #e6e6e6;
    border: 1px solid #4a4a4f;
}
QPushButton#secondary:hover { background-color: #3d3d42; }
QPushButton#danger {
    background-color: transparent;
    color: #ffffff;
    border: 1px solid #ffffff;
}
QPushButton#danger:hover { background-color: #2a4b8f; }
QPushButton#navItem {
    text-align: left;
    padding: 10px 12px;
    border: none;
    border-bottom: 1px solid #35353a;
    border-radius: 0;
    background-color: #2b2b2e;
    color: #bdbdbd;
    font-weight: 400;
}
QPushButton#navItem:hover { background-color: #333338; }
QPushButton#navItem[current="true"] {
    background-color: #1c1c1f;
    color: #ffffff;
    border-left: 3px solid #4f83c9;
    font-weight: 600;
}
QPushButton#navItem[answered="true"] {
    background-color: #345d8f;
    color: #ffffff;
}
QPushButton#navItem[answered="true"][current="true"] {
    background-color: #3f6fb0;
    border-left: 3px solid #ffffff;
}
QPushButton#navItem:disabled { background-color: #2b2b2e; color: #6f6f6f; }
QScrollArea { border: none; background-color: transparent; }
QLabel#taskTitle { font-size: 20px; font-weight: 700; color: #ffffff; }
QLabel#section { font-size: 15px; font-weight: 600; color: #c7cdd8; }
QTableWidget {
    background-color: #2d2d30;
    border: 1px solid #3f3f46;
    gridline-color: #3a3a40;
    color: #e6e6e6;
}
QHeaderView::section {
    background-color: #333336;
    color: #e6e6e6;
    border: none;
    border-bottom: 1px solid #3f3f46;
    padding: 8px;
    font-weight: 600;
}
QMessageBox { background-color: #2d2d30; }
QMessageBox QLabel { color: #e6e6e6; }
QScrollBar:vertical { background: transparent; width: 10px; }
QScrollBar::handle:vertical { background: #4a4a4f; border-radius: 5px; }
QScrollBar::handle:vertical:hover { background: #5a5a60; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal { background: transparent; height: 10px; }
QScrollBar::handle:horizontal { background: #4a4a4f; border-radius: 5px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""