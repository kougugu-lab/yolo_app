# -*- coding: utf-8 -*-
"""QSS ダークテーマ定義"""

DARK_THEME_QSS = """
/* ===== 全体 ===== */
QWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    font-family: "Yu Gothic UI", "Segoe UI", sans-serif;
    font-size: 15px;
}

/* ===== メインウィンドウ ===== */
QMainWindow {
    background-color: #1e1e1e;
}

/* ===== グループボックス ===== */
QGroupBox {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 6px;
    margin-top: 12px;
    padding: 18px 12px 12px 12px;
    font-weight: bold;
    font-size: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: #82aaff;
}

/* ===== ボタン（通常） ===== */
QPushButton {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #4a4a4a;
    border-radius: 6px;
    padding: 10px 20px;
    min-height: 28px;
    font-size: 15px;
}
QPushButton:hover {
    background-color: #3a3a3a;
    border-color: #5a5a5a;
}
QPushButton:pressed {
    background-color: #1a1a1a;
}
QPushButton:disabled {
    background-color: #252525;
    color: #555555;
    border-color: #333333;
}

/* ===== アクセントボタン (objectName: accentButton) ===== */
QPushButton#accentButton,
QPushButton[accent="true"] {
    background-color: #0078d7;
    color: #ffffff;
    border: none;
    font-weight: bold;
}
QPushButton#accentButton:hover,
QPushButton[accent="true"]:hover {
    background-color: #1a8ae8;
}
QPushButton#accentButton:pressed,
QPushButton[accent="true"]:pressed {
    background-color: #005fa3;
}

/* ===== 停止ボタン (objectName: stopButton) ===== */
QPushButton#stopButton {
    background-color: #8b0000;
    color: #ffffff;
    border: 1px solid #a00000;
    font-weight: bold;
}
QPushButton#stopButton:hover {
    background-color: #a80000;
}
QPushButton#stopButton:pressed {
    background-color: #5c0000;
}
QPushButton#stopButton:disabled {
    background-color: #2d2020;
    color: #665555;
    border-color: #3d2d2d;
}

/* ===== ステップボタン ===== */
QPushButton[step="true"] {
    background-color: #0078d7;
    color: #ffffff;
    border: none;
    border-radius: 6px;
    padding: 14px 16px;
    font-weight: bold;
    font-size: 17px;
    text-align: left;
}
QPushButton[step="true"]:hover {
    background-color: #1a8ae8;
}
QPushButton[step="true"]:pressed {
    background-color: #005fa3;
}
QPushButton[step="true"]:disabled {
    background-color: #1a3a5c;
    color: #6a8aaa;
}

/* ===== テキスト入力 ===== */
QLineEdit, QSpinBox, QDoubleSpinBox {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 5px 24px 5px 8px; /* 右側にスピンボタン用スペースを確保 */
    selection-background-color: #0078d7;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {
    border-color: #0078d7;
}

/* ===== スピンボタン (SpinBox Buttons) ===== */
QSpinBox::up-button, QDoubleSpinBox::up-button {
    subcontrol-origin: border;
    subcontrol-position: top right;
    width: 22px;
    border-left: 1px solid #4a4a4a;
    border-bottom: 1px solid #4a4a4a;
    background-color: #383838;
    border-top-right-radius: 3px;
}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
    background-color: #4a4a4a;
}
QSpinBox::down-button, QDoubleSpinBox::down-button {
    subcontrol-origin: border;
    subcontrol-position: bottom right;
    width: 22px;
    border-left: 1px solid #4a4a4a;
    background-color: #383838;
    border-bottom-right-radius: 3px;
}
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
    background-color: #4a4a4a;
}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid #e0e0e0;
    width: 0px;
    height: 0px;
}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid #e0e0e0;
    width: 0px;
    height: 0px;
}

/* ===== コンボボックス ===== */
QComboBox {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 5px 8px;
    min-height: 22px;
}
QComboBox:hover {
    border-color: #5a5a5a;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid #e0e0e0;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #e0e0e0;
    selection-background-color: #0078d7;
    border: 1px solid #4a4a4a;
}

/* ===== スライダー ===== */
QSlider::groove:horizontal {
    background: #3a3a3a;
    height: 6px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #0078d7;
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}
QSlider::handle:horizontal:hover {
    background: #1a8ae8;
}
QSlider::sub-page:horizontal {
    background: #0078d7;
    border-radius: 3px;
}

/* ===== プログレスバー ===== */
QProgressBar {
    background-color: #2d2d2d;
    border: 1px solid #3a3a3a;
    border-radius: 4px;
    text-align: center;
    color: #e0e0e0;
    min-height: 18px;
    font-size: 11px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #0078d7, stop:1 #00b4d8);
    border-radius: 3px;
}

/* ===== ログエリア ===== */
QTextEdit#logArea {
    background-color: #1a1a2e;
    color: #c8d6e5;
    border: 1px solid #2a2a4a;
    border-radius: 6px;
    padding: 8px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 14px;
}

/* ===== スクロールバー ===== */
QScrollBar:vertical {
    background-color: #1e1e1e;
    width: 10px;
    border: none;
}
QScrollBar::handle:vertical {
    background-color: #4a4a4a;
    min-height: 30px;
    border-radius: 5px;
}
QScrollBar::handle:vertical:hover {
    background-color: #5a5a5a;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    background-color: #1e1e1e;
    height: 10px;
    border: none;
}
QScrollBar::handle:horizontal {
    background-color: #4a4a4a;
    min-width: 30px;
    border-radius: 5px;
}

/* ===== ラベル ===== */
QLabel {
    color: #e0e0e0;
    background-color: transparent;
}
QLabel#headerLabel {
    font-size: 24px;
    font-weight: bold;
    color: #82aaff;
    padding: 8px 0px;
}
QLabel#sectionLabel {
    font-size: 18px;
    font-weight: bold;
    color: #c3e88d;
    padding: 4px 0px;
}

/* ===== ダイアログ ===== */
QDialog {
    background-color: #1e1e1e;
}

/* ===== タブ ===== */
QTabWidget::pane {
    border: 1px solid #3a3a3a;
    background-color: #2a2a2a;
    border-radius: 4px;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #a0a0a0;
    padding: 8px 18px;
    border: 1px solid #3a3a3a;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #2a2a2a;
    color: #e0e0e0;
    border-bottom: 2px solid #0078d7;
}
QTabBar::tab:hover:!selected {
    background-color: #353535;
}

/* ===== プレーンテキスト入力 ===== */
QPlainTextEdit {
    background-color: #2d2d2d;
    color: #e0e0e0;
    border: 1px solid #4a4a4a;
    border-radius: 4px;
    padding: 6px;
    font-family: "Cascadia Code", "Consolas", monospace;
    font-size: 12px;
    selection-background-color: #0078d7;
}
QPlainTextEdit:focus {
    border-color: #0078d7;
}

/* ===== メッセージボックス ===== */
QMessageBox {
    background-color: #1e1e1e;
}
QMessageBox QLabel {
    color: #e0e0e0;
}
"""
