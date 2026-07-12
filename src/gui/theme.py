# ============================================================================
# Project X — Blue Theme (RC-003)
# ============================================================================

from __future__ import annotations

# --- Backgrounds (dark UI preserved) ----------------------------------------

BG_DEEP = "#1d2127"
BG_BASE = "#252a31"
BG_RAISED = "#2a3140"
BG_HEADER = "#2a3548"
BG_PANEL = "#353b44"

# --- Project X Blue accents (replaces neutral gray interactive surfaces) ----

BG_BUTTON = "#243651"
BG_BUTTON_HOVER = "#2d4a6f"
BG_NAV_HOVER = "#243651"
BG_NAV_ACTIVE = "#1e3a5f"

BORDER = "#3d4a5c"
BORDER_STRONG = "#2d5a8e"
BORDER_FOCUS = "#4fc3f7"

ACCENT = "#1976d2"
ACCENT_HOVER = "#1e88e5"
ACCENT_ACTIVE = "#1565c0"
ACCENT_LIGHT = "#29b6f6"
ACCENT_GLOW = "#4fc3f7"

# --- Text -------------------------------------------------------------------

TEXT = "#d5dbe3"
TEXT_PRIMARY = "#ffffff"
TEXT_MUTED = "#9aa4af"
TEXT_SOFT = "#7a8494"
TEXT_DISABLED = "#7a8494"

# --- Semantic (unchanged for readability) -----------------------------------

SUCCESS = "#66bb6a"
WARNING = "#ffb74d"
ERROR = "#ef5350"


def card_stylesheet(*, radius: int = 10) -> str:

    return f"""
        QFrame {{
            background: {BG_BASE};
            border: 1px solid {BORDER};
            border-radius: {radius}px;
        }}
    """


def primary_button_stylesheet(*, padding: str = "8px 12px") -> str:

    return f"""
        QPushButton {{
            background: {ACCENT};
            color: {TEXT_PRIMARY};
            border: none;
            border-radius: 6px;
            padding: {padding};
        }}
        QPushButton:hover {{
            background: {ACCENT_HOVER};
        }}
        QPushButton:disabled {{
            background: {BORDER_STRONG};
            color: {TEXT_SOFT};
        }}
        QPushButton:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}
    """


def secondary_button_stylesheet(*, padding: str = "6px 12px") -> str:

    return f"""
        QPushButton {{
            background: {BG_BUTTON};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER_STRONG};
            border-radius: 6px;
            padding: {padding};
        }}
        QPushButton:hover {{
            background: {BG_BUTTON_HOVER};
        }}
        QPushButton:disabled {{
            color: {TEXT_DISABLED};
        }}
        QPushButton:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}
    """


def table_stylesheet() -> str:

    return f"""
        QTableWidget {{
            background: {BG_BASE};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            gridline-color: {BORDER};
            selection-background-color: {ACCENT};
            selection-color: {TEXT_PRIMARY};
        }}
        QHeaderView::section {{
            background: {BG_HEADER};
            color: {TEXT};
            border: 1px solid {BORDER};
            padding: 6px;
        }}
        QTableWidget::item:selected {{
            background: {ACCENT};
        }}
    """


def input_stylesheet() -> str:

    return f"""
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
            background: {BG_DEEP};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 6px 8px;
        }}
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
        QTextEdit:focus, QPlainTextEdit:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background: {BG_BASE};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            selection-background-color: {ACCENT};
            selection-color: {TEXT_PRIMARY};
        }}
    """


def sidebar_stylesheet() -> str:

    return f"""
        QFrame {{
            background: {BG_DEEP};
            border-right: 1px solid {BORDER};
        }}

        QPushButton {{
            color: {TEXT_PRIMARY};
            background: transparent;
            border: none;
            text-align: left;
            padding: 10px;
            font-size: 12pt;
        }}

        QPushButton:hover {{
            background: {BG_NAV_HOVER};
        }}

        QPushButton:checked {{
            background: {BG_NAV_ACTIVE};
            color: {ACCENT_GLOW};
        }}

        QPushButton:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}
    """


def global_stylesheet() -> str:

    return f"""
        QWidget {{
            background: {BG_DEEP};
            color: {TEXT};
        }}

        QMainWindow {{
            background: {BG_DEEP};
        }}

        QDialog {{
            background: {BG_DEEP};
            color: {TEXT};
        }}

        QMenuBar {{
            background: {BG_DEEP};
            color: {TEXT};
            border-bottom: 1px solid {BORDER};
        }}

        QMenuBar::item:selected {{
            background: {BG_NAV_ACTIVE};
            color: {ACCENT_GLOW};
        }}

        QMenu {{
            background: {BG_BASE};
            color: {TEXT};
            border: 1px solid {BORDER};
        }}

        QMenu::item:selected {{
            background: {ACCENT};
            color: {TEXT_PRIMARY};
        }}

        QStatusBar {{
            background: {BG_BASE};
            color: {TEXT_MUTED};
            border-top: 1px solid {BORDER};
        }}

        QScrollArea {{
            background: transparent;
            border: none;
        }}

        QScrollBar:vertical {{
            background: {BG_DEEP};
            width: 12px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background: {BG_BUTTON};
            border-radius: 4px;
            min-height: 24px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {ACCENT};
        }}

        QScrollBar:horizontal {{
            background: {BG_DEEP};
            height: 12px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background: {BG_BUTTON};
            border-radius: 4px;
            min-width: 24px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {ACCENT};
        }}

        QCheckBox, QRadioButton {{
            color: {TEXT};
            spacing: 8px;
        }}

        QCheckBox::indicator, QRadioButton::indicator {{
            width: 16px;
            height: 16px;
            border: 1px solid {BORDER_STRONG};
            background: {BG_DEEP};
        }}

        QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
            background: {ACCENT};
            border-color: {ACCENT_HOVER};
        }}

        QCheckBox::indicator:focus, QRadioButton::indicator:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}

        QGroupBox {{
            color: {TEXT};
            border: 1px solid {BORDER};
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
            color: {ACCENT_LIGHT};
        }}

        QToolTip {{
            background: {BG_BASE};
            color: {TEXT};
            border: 1px solid {BORDER_FOCUS};
        }}

        QListWidget {{
            background: {BG_BASE};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            outline: none;
        }}

        QListWidget::item:selected {{
            background: {ACCENT};
            color: {TEXT_PRIMARY};
        }}

        QListWidget::item:hover {{
            background: {BG_NAV_HOVER};
        }}

        {input_stylesheet()}
    """
