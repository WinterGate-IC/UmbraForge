"""UmbraForge's dark visual language.

One stylesheet, one palette, no theme picker - the studio is dark by design.
The colours below are also used by the canvas for its checkerboard, guides and
selection chrome.
"""

from __future__ import annotations

WINDOW = "#08080c"
PANEL = "#0f0f17"
PANEL_ALT = "#13131d"
FIELD = "#0b0b11"
RAISED = "#1a1a27"
RAISED_HOVER = "#232334"
BORDER = "#262636"
BORDER_HOVER = "#3a3a52"
TEXT = "#f3f1f8"
TEXT_MUTED = "#9b97ad"
TEXT_DISABLED = "#5e5b70"
ACCENT = "#ff7a3d"
ACCENT_STRONG = "#f2622a"
ACCENT_HOVER = "#ff8f5c"
ACCENT_SOFT = "#2b1a14"
ACCENT_DIM = "#7a3a1e"
VIOLET = "#8b5cf6"
VIOLET_SOFT = "#1b1430"
SELECTION = "#5b3b9e"
DANGER = "#ff5c72"
DANGER_BG = "#43141c"
OK = "#4ade80"
WARN = "#fbbf24"
PILL_BG = "#241a2e"
PILL_TEXT = "#d7c9ea"
CANVAS_BG = "#06060a"
CHECKER_A = "#14141c"
CHECKER_B = "#1b1b26"

FONT_FAMILY = "Segoe UI"


def build_palette():
    from PySide6.QtGui import QColor, QPalette

    palette = QPalette()
    roles = {
        QPalette.ColorRole.Window: WINDOW,
        QPalette.ColorRole.WindowText: TEXT,
        QPalette.ColorRole.Base: FIELD,
        QPalette.ColorRole.AlternateBase: PANEL,
        QPalette.ColorRole.ToolTipBase: RAISED,
        QPalette.ColorRole.ToolTipText: TEXT,
        QPalette.ColorRole.Text: TEXT,
        QPalette.ColorRole.Button: RAISED,
        QPalette.ColorRole.ButtonText: TEXT,
        QPalette.ColorRole.BrightText: DANGER,
        QPalette.ColorRole.Link: ACCENT,
        QPalette.ColorRole.Highlight: SELECTION,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: TEXT_DISABLED,
    }
    for role, colour in roles.items():
        palette.setColor(role, QColor(colour))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(TEXT_DISABLED))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Base,
                     QColor(PANEL))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Button,
                     QColor(PANEL))
    palette.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight,
                     QColor(BORDER))
    return palette


def stylesheet() -> str:
    return f"""
QMainWindow, QDialog {{ background: {WINDOW}; }}
QWidget {{ color: {TEXT}; font-family: "{FONT_FAMILY}"; font-size: 12px; }}
QWidget#page {{ background: {WINDOW}; }}
QWidget#leftRail, QWidget#rightRail, QWidget#topBar {{
    background: {PANEL};
}}
QWidget#leftRail {{ border-right: 1px solid {BORDER}; }}
QWidget#rightRail {{ border-left: 1px solid {BORDER}; }}
QWidget#topBar {{ border-bottom: 1px solid {BORDER}; }}
QWidget#statusBar {{ background: {PANEL}; border-top: 1px solid {BORDER}; }}

QLabel#brand {{ font-size: 17px; font-weight: 800; letter-spacing: 1.4px; }}
QLabel#title {{ font-size: 22px; font-weight: 800; }}
QLabel#heading {{ font-size: 13px; font-weight: 700; }}
QLabel#sectionLabel {{
    color: {TEXT_MUTED}; font-size: 10px; font-weight: 700;
    letter-spacing: 1.2px;
}}
QLabel#muted {{ color: {TEXT_MUTED}; }}
QLabel#hint {{ color: {TEXT_DISABLED}; font-size: 11px; }}
QLabel#pill {{
    background: {PILL_BG}; color: {PILL_TEXT}; border-radius: 8px;
    padding: 1px 8px; font-size: 10px; font-weight: 700;
}}
QLabel#tag {{
    color: {ACCENT}; font-size: 10px; font-weight: 700; letter-spacing: .6px;
}}
QLabel#dim {{ color: {TEXT_MUTED}; font-size: 11px; }}

QFrame#card {{
    background: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 10px;
}}
QFrame#card:hover {{ border-color: {BORDER_HOVER}; }}
QFrame#card[selected="true"] {{
    border: 1px solid {ACCENT}; background: {ACCENT_SOFT};
}}
QFrame#rule {{ background: {BORDER}; max-height: 1px; border: 0; }}

QPushButton {{
    background: {RAISED}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 7px; padding: 6px 12px;
}}
QPushButton:hover {{ background: {RAISED_HOVER}; border-color: {BORDER_HOVER}; }}
QPushButton:pressed {{ background: {ACCENT_SOFT}; }}
QPushButton:disabled {{
    background: {PANEL}; color: {TEXT_DISABLED}; border-color: {BORDER};
}}
QPushButton#primary {{
    background: {ACCENT_STRONG}; color: #ffffff; border: none;
    font-weight: 700; padding: 9px 16px;
}}
QPushButton#primary:hover {{ background: {ACCENT_HOVER}; }}
QPushButton#primary:disabled {{ background: {PANEL}; color: {TEXT_DISABLED}; }}
QPushButton#ghost {{
    background: transparent; border: 1px solid transparent;
    color: {TEXT_MUTED};
}}
QPushButton#ghost:hover {{ background: {RAISED}; color: {TEXT}; }}
QPushButton#danger {{ color: {DANGER}; }}
QPushButton#danger:hover {{
    background: {DANGER_BG}; border-color: {DANGER}; color: #ffffff;
}}
QPushButton#chip {{
    background: {PANEL_ALT}; border: 1px solid {BORDER}; border-radius: 13px;
    padding: 4px 11px; color: {TEXT_MUTED}; font-size: 11px;
}}
QPushButton#chip:hover {{ border-color: {ACCENT_DIM}; color: {TEXT}; }}
QPushButton#chip:checked {{
    background: {ACCENT_SOFT}; border-color: {ACCENT}; color: {ACCENT};
}}

QToolButton {{
    background: transparent; border: 1px solid transparent; border-radius: 6px;
    padding: 5px 8px; color: {TEXT_MUTED};
}}
QToolButton:hover {{ background: {RAISED}; color: {TEXT}; }}
QToolButton:pressed {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}
QToolButton:checked {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}
QToolButton#railTab {{
    padding: 8px 6px; font-size: 10px; font-weight: 700; letter-spacing: .5px;
}}

QTabWidget::pane {{
    border: 0; border-top: 1px solid {BORDER}; background: transparent;
}}
QTabBar {{ background: transparent; }}
QTabBar::tab {{
    background: transparent; color: {TEXT_MUTED}; padding: 8px 12px;
    border: 0; border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:hover {{ color: {TEXT}; }}
QTabBar::tab:selected {{ color: {TEXT}; border-bottom-color: {ACCENT}; }}

QGroupBox {{
    background: transparent; border: 0; margin-top: 14px;
    padding-top: 8px; font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin; left: 0; padding: 0 4px;
    color: {TEXT_MUTED}; font-size: 10px; font-weight: 700;
    letter-spacing: 1.1px;
}}

QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox {{
    background: {FIELD}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 5px 7px;
    selection-background-color: {SELECTION}; selection-color: #ffffff;
}}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACCENT}; }}
QLineEdit:disabled, QPlainTextEdit:disabled, QTextEdit:disabled,
QSpinBox:disabled, QDoubleSpinBox:disabled {{
    color: {TEXT_DISABLED}; background: {PANEL};
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    width: 14px; border: 0; background: transparent;
}}

QComboBox {{
    background: {RAISED}; color: {TEXT}; border: 1px solid {BORDER};
    border-radius: 6px; padding: 4px 9px; min-height: 20px;
}}
QComboBox:hover {{ border-color: {BORDER_HOVER}; }}
QComboBox::drop-down {{ border: 0; width: 18px; }}
QComboBox QAbstractItemView {{
    background: {PANEL}; color: {TEXT}; border: 1px solid {BORDER};
    selection-background-color: {SELECTION}; selection-color: #ffffff;
    outline: 0; padding: 3px;
}}

QSlider::groove:horizontal {{
    height: 5px; background: {BORDER}; border-radius: 2px;
}}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {TEXT}; width: 12px; height: 12px;
    margin: -4px 0; border-radius: 6px; border: 2px solid {PANEL};
}}
QSlider::handle:horizontal:hover {{ background: #ffffff; }}
QSlider::handle:horizontal:disabled {{ background: {TEXT_DISABLED}; }}
QSlider::groove:horizontal:disabled {{ background: {BORDER}; }}

QScrollBar:vertical {{ background: transparent; width: 11px; margin: 0; }}
QScrollBar::handle:vertical {{
    background: {BORDER}; min-height: 28px; border-radius: 5px;
}}
QScrollBar::handle:vertical:hover {{ background: {BORDER_HOVER}; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 0; }}
QScrollBar::handle:horizontal {{
    background: {BORDER}; min-width: 28px; border-radius: 5px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QCheckBox {{ spacing: 7px; color: {TEXT}; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; border-radius: 4px;
    border: 1px solid {BORDER_HOVER}; background: {FIELD};
}}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{
    background: {ACCENT}; border-color: {ACCENT};
    image: none;
}}
QRadioButton {{ spacing: 7px; }}

QListWidget, QTreeWidget, QListView, QTreeView {{
    background: transparent; border: 0; outline: 0;
}}
QListWidget::item {{ padding: 0; border-radius: 7px; }}
QListWidget::item:hover {{ background: {PANEL_ALT}; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; }}

QScrollArea {{ border: 0; background: transparent; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QSplitter::handle {{ background: {BORDER}; width: 1px; }}
QSplitter::handle:hover {{ background: {ACCENT_DIM}; }}

QMenuBar {{ background: {PANEL}; color: {TEXT_MUTED}; border-bottom: 1px solid {BORDER}; }}
QMenuBar::item {{ padding: 5px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {RAISED}; color: {TEXT}; }}
QMenu {{ background: {PANEL}; border: 1px solid {BORDER}; padding: 5px; }}
QMenu::item {{ padding: 6px 26px 6px 20px; border-radius: 5px; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; color: {ACCENT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QToolTip {{
    background: {RAISED}; color: {TEXT}; border: 1px solid {BORDER_HOVER};
    padding: 4px 7px;
}}
QStatusBar {{
    background: {PANEL}; color: {TEXT_MUTED};
    border-top: 1px solid {BORDER};
}}
QStatusBar QLabel {{ color: {TEXT_MUTED}; padding: 0 4px; }}
QProgressBar {{
    background: {FIELD}; border: 1px solid {BORDER}; border-radius: 5px;
    text-align: center; color: {TEXT}; min-height: 14px; max-height: 14px;
    font-size: 10px;
}}
QProgressBar::chunk {{ background: {ACCENT_STRONG}; border-radius: 4px; }}
QDialogButtonBox {{ background: transparent; }}
QColorDialog {{ background: {PANEL}; }}
QColorDialog QLabel {{ color: {TEXT}; }}
"""


def apply(app) -> None:
    app.setStyle("Fusion")
    app.setPalette(build_palette())
    app.setStyleSheet(stylesheet())
    app.setProperty("umbraforge_theme", "ember")
