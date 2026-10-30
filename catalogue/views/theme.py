"""The app's light theme: colours and button styles in one place.

Qt's "Fusion" style looks the same on macOS, Windows and Linux. We give it a
fixed light palette (so it stays light even when the Mac is in dark mode)
and a small style sheet for the buttons, inputs, table and status bar.

Widgets get a special look through their objectName:
  "primaryButton"  blue button for the main action (Save Details)
  "dangerButton"   red text for actions that remove or stop something
"""
from PyQt6.QtGui import QColor, QPalette

BLUE = "#2f6fed"
BLUE_DARK = "#2459c9"
BLUE_LIGHT = "#e8f0fe"
RED = "#c62828"
RED_LIGHT = "#fdecec"
TEXT = "#1f2933"
MUTED = "#6b7785"
BORDER = "#cfd6de"
PANEL = "#f5f6f8"
STAR = "#e0a100"

STYLE_SHEET = f"""
QToolBar {{
    background: {PANEL};
    border: none;
    border-bottom: 1px solid #dfe3e8;
    padding: 6px;
    spacing: 6px;
}}
QToolBar QToolButton {{
    background: white;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 10px;
}}
QToolBar QToolButton:hover {{ background: {BLUE_LIGHT}; border-color: {BLUE}; }}
QToolBar QToolButton:pressed {{ background: #d4e2fc; }}
QToolBar QToolButton:disabled {{ color: #a3abb5; background: #f0f2f4; border-color: #e3e6ea; }}
QToolBar QToolButton#dangerButton {{ color: {RED}; border-color: #e8b4b4; }}
QToolBar QToolButton#dangerButton:hover {{ background: {RED_LIGHT}; border-color: {RED}; }}
QToolBar QToolButton#dangerButton:disabled {{ color: #a3abb5; border-color: #e3e6ea; }}

QPushButton {{
    background: white;
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{ background: {BLUE_LIGHT}; border-color: {BLUE}; }}
QPushButton:disabled {{ color: #a3abb5; background: #f0f2f4; border-color: #e3e6ea; }}
QPushButton#primaryButton {{
    background: {BLUE};
    color: white;
    border-color: {BLUE};
    font-weight: bold;
}}
QPushButton#primaryButton:hover {{ background: {BLUE_DARK}; }}
QPushButton#primaryButton:disabled {{ background: #a9c1f5; border-color: #a9c1f5; color: white; }}
QPushButton#dangerButton {{ color: {RED}; border-color: #e8b4b4; }}
QPushButton#dangerButton:hover {{ background: {RED_LIGHT}; border-color: {RED}; }}

QLineEdit {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 5px 8px;
}}
QLineEdit:focus {{ border-color: {BLUE}; }}
QLineEdit:disabled {{ background: #f0f2f4; color: #a3abb5; }}

QGroupBox {{
    background: white;
    border: 1px solid #dfe3e8;
    border-radius: 8px;
    margin-top: 14px;
    padding: 12px 8px 8px 8px;
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
    color: {MUTED};
}}

QTableView {{
    background: white;
    alternate-background-color: #f8f9fb;
    border: 1px solid #dfe3e8;
    border-radius: 6px;
    gridline-color: #eef0f3;
    selection-background-color: #d4e2fc;
    selection-color: {TEXT};
}}
QHeaderView::section {{
    background: #f0f2f5;
    color: #3e4c59;
    border: none;
    border-right: 1px solid #e3e6ea;
    border-bottom: 1px solid #dfe3e8;
    padding: 6px;
    font-weight: bold;
}}

QProgressBar {{
    background: #e9ecf0;
    border: none;
    border-radius: 6px;
    text-align: center;
    min-height: 14px;
    max-height: 14px;
    font-size: 11px;
}}
QProgressBar::chunk {{ background: {BLUE}; border-radius: 6px; }}

QStatusBar {{ background: {PANEL}; border-top: 1px solid #dfe3e8; }}
QStatusBar QLabel#countLabel {{ color: {MUTED}; font-weight: bold; padding: 0 8px; }}
QSplitter::handle {{ background: {PANEL}; width: 6px; }}
"""


def light_palette():
    palette = QPalette()
    colours = {
        QPalette.ColorRole.Window: PANEL,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: "white",
        QPalette.ColorRole.AlternateBase: "#f8f9fb",
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.Button: "white",
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.Highlight: BLUE,
        QPalette.ColorRole.HighlightedText: "white",
        QPalette.ColorRole.ToolTipBase: "white",
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.PlaceholderText: "#8a94a0",
        QPalette.ColorRole.Link: BLUE,
    }
    for role, colour in colours.items():
        palette.setColor(role, QColor(colour))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#a3abb5"))
    return palette


def apply_light_theme(app):
    """Call once, right after creating the QApplication."""
    app.setStyle("Fusion")
    app.setPalette(light_palette())
    app.setStyleSheet(STYLE_SHEET)
