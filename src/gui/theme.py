# ============================================================================
# Project X — Design System (SAVE-102)
# ============================================================================

from __future__ import annotations


class ThemeColors:
    """Official Project X palette — single source of truth."""

    # --- Surfaces -------------------------------------------------------------

    Background = "#1d2127"
    Panel = "#252a31"
    PanelHover = "#3b434d"
    Border = "#3d4a5c"
    BorderActive = "#4a6fa0"

    # --- Primary scale (muted blue-gray) --------------------------------------

    Primary900 = "#243651"
    Primary700 = "#2d4a6f"
    Primary500 = "#4a6fa0"
    Primary300 = "#6d8fb3"
    Primary100 = "#9eb3c9"

    # --- Text -----------------------------------------------------------------

    TextPrimary = "#ffffff"
    TextSecondary = "#9aa4af"

    # --- Semantic -------------------------------------------------------------

    Success = "#66bb6a"
    Warning = "#ffb74d"
    Danger = "#ef5350"

    @classmethod
    def primary_hover(cls) -> str:
        """Primary action / button hover."""

        return "#3d5f85"

    @classmethod
    def primary_active(cls) -> str:
        """Primary action / button pressed."""

        return "#355472"

    @classmethod
    def nav_active_background(cls) -> str:
        """Selected navigation item background."""

        return cls.Primary700

    @classmethod
    def panel_header(cls) -> str:
        """Table headers and elevated panel chrome."""

        return "#2a3548"

    @classmethod
    def panel_elevated(cls) -> str:
        """Raised panel surfaces (e.g. camera preview)."""

        return "#353b44"

    @classmethod
    def text_body(cls) -> str:
        """Default body copy on dark surfaces."""

        return "#d5dbe3"

    @classmethod
    def text_soft(cls) -> str:
        """De-emphasized labels and disabled-adjacent text."""

        return "#7a8494"


# --- Backward-compatible aliases (prefer ThemeColors in new code) ------------

BG_DEEP = ThemeColors.Background
BG_BASE = ThemeColors.Panel
BG_RAISED = "#2a3140"
BG_HEADER = ThemeColors.panel_header()
BG_PANEL = ThemeColors.panel_elevated()

BG_BUTTON = ThemeColors.Primary900
BG_BUTTON_HOVER = ThemeColors.Primary700
BG_NAV_HOVER = ThemeColors.Primary900
BG_NAV_ACTIVE = ThemeColors.nav_active_background()

BORDER = ThemeColors.Border
BORDER_STRONG = ThemeColors.Primary700
BORDER_FOCUS = ThemeColors.Primary300

ACCENT = ThemeColors.Primary500
ACCENT_HOVER = ThemeColors.primary_hover()
ACCENT_ACTIVE = ThemeColors.primary_active()
ACCENT_LIGHT = ThemeColors.Primary100
ACCENT_GLOW = ThemeColors.Primary100

TEXT = ThemeColors.text_body()
TEXT_PRIMARY = ThemeColors.TextPrimary
TEXT_MUTED = ThemeColors.TextSecondary
TEXT_SOFT = ThemeColors.text_soft()
TEXT_DISABLED = ThemeColors.text_soft()

SUCCESS = ThemeColors.Success
WARNING = ThemeColors.Warning
ERROR = ThemeColors.Danger
DANGER = ThemeColors.Danger


def card_stylesheet(*, radius: int = 10) -> str:

    return f"""
        QFrame {{
            background: {ThemeColors.Panel};
            border: 1px solid {ThemeColors.Border};
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
        QPushButton:pressed {{
            background: {ACCENT_ACTIVE};
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
            background: {ThemeColors.Panel};
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
            background: {ThemeColors.Panel};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            selection-background-color: {ACCENT};
            selection-color: {TEXT_PRIMARY};
        }}
    """


def sidebar_stylesheet() -> str:

    return f"""
        QFrame {{
            background: {ThemeColors.Background};
            border-right: 1px solid {ThemeColors.Border};
        }}

        QPushButton {{
            color: {TEXT_PRIMARY};
            background: transparent;
            border: none;
            text-align: left;
            padding: 10px;
            font-size: 12pt;
            border-radius: 6px;
        }}

        QPushButton:hover {{
            background: {ThemeColors.PanelHover};
        }}

        QPushButton:checked {{
            background: {BG_NAV_ACTIVE};
            color: {ACCENT_GLOW};
            font-weight: 600;
        }}

        QPushButton:focus {{
            border: 1px solid {BORDER_FOCUS};
        }}
    """


def wizard_shell_stylesheet(*, include_disabled: bool = False) -> str:

    disabled_rule = ""

    if include_disabled:
        disabled_rule = f"""
        QPushButton:disabled {{
            color: {TEXT_DISABLED};
        }}
        """

    return f"""
        QDialog {{
            background: {BG_DEEP};
        }}

        QLabel {{
            color: {TEXT};
        }}

        QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
            background: {ThemeColors.Panel};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 6px 8px;
        }}

        QCheckBox, QRadioButton {{
            color: {TEXT};
        }}

        {disabled_rule}

        {secondary_button_stylesheet()}
    """


def data_panel_stylesheet() -> str:

    return f"""
        QCheckBox {{
            color: {TEXT};
        }}

        QComboBox, QLineEdit {{
            background: {ThemeColors.Panel};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 6px 8px;
        }}

        {primary_button_stylesheet()}

        {table_stylesheet()}
    """


def analytics_page_stylesheet() -> str:

    return f"""
        QLabel[role="title"] {{
            color: {TEXT_PRIMARY};
            font-size: 26pt;
            font-weight: bold;
        }}

        QLabel[role="summary-title"] {{
            color: {TEXT_MUTED};
            font-size: 9pt;
            font-weight: 600;
        }}

        QLabel[role="summary-value"] {{
            color: {TEXT_PRIMARY};
            font-size: 16pt;
            font-weight: bold;
        }}

        QLabel[role="field"] {{
            color: {TEXT};
            font-size: 10pt;
            font-weight: 600;
        }}

        {data_panel_stylesheet()}
    """


def settings_panel_stylesheet(*, include_table: bool = False, radius: int = 10) -> str:

    table_block = table_stylesheet() if include_table else ""

    return f"""
        QFrame {{
            background: {ThemeColors.Panel};
            border: 1px solid {BORDER};
            border-radius: {radius}px;
            padding: 4px;
        }}

        QLabel[role="section"] {{
            color: {TEXT};
            font-size: 12pt;
            font-weight: 600;
        }}

        QLabel[role="field"] {{
            color: {TEXT_MUTED};
            font-size: 10pt;
            font-weight: 600;
        }}

        QLabel[role="caption"] {{
            color: {TEXT_SOFT};
            font-size: 9pt;
        }}

        QLabel[role="summary-title"] {{
            color: {TEXT_MUTED};
            font-size: 9pt;
            font-weight: 600;
        }}

        QLabel[role="summary-value"] {{
            color: {TEXT_PRIMARY};
            font-size: 16pt;
            font-weight: bold;
        }}

        QComboBox, QLineEdit {{
            background: {BG_DEEP};
            color: {TEXT_PRIMARY};
            border: 1px solid {BORDER};
            border-radius: 6px;
            padding: 6px 8px;
        }}

        {primary_button_stylesheet()}

        {table_block}
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
            background: {ThemeColors.Panel};
            color: {TEXT};
            border: 1px solid {BORDER};
        }}

        QMenu::item:selected {{
            background: {ACCENT};
            color: {TEXT_PRIMARY};
        }}

        QStatusBar {{
            background: {ThemeColors.Panel};
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
            background: {ThemeColors.Panel};
            color: {TEXT};
            border: 1px solid {BORDER_FOCUS};
        }}

        QListWidget {{
            background: {ThemeColors.Panel};
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

        QProgressBar {{
            background: {BG_DEEP};
            border: 1px solid {BORDER};
            border-radius: 4px;
            text-align: center;
            color: {TEXT_PRIMARY};
        }}

        QProgressBar::chunk {{
            background: {ACCENT};
            border-radius: 3px;
        }}

        QSlider::groove:horizontal {{
            background: {BG_DEEP};
            border: 1px solid {BORDER};
            height: 6px;
            border-radius: 3px;
        }}

        QSlider::handle:horizontal {{
            background: {ACCENT};
            border: 1px solid {ACCENT_HOVER};
            width: 14px;
            margin: -5px 0;
            border-radius: 7px;
        }}

        QSlider::handle:horizontal:hover {{
            background: {ACCENT_HOVER};
        }}

        {input_stylesheet()}
    """


class ProjectXTheme:
    """Project X Design System — centralized colors and stylesheets."""

    Colors = ThemeColors

    card_stylesheet = staticmethod(card_stylesheet)
    primary_button_stylesheet = staticmethod(primary_button_stylesheet)
    secondary_button_stylesheet = staticmethod(secondary_button_stylesheet)
    table_stylesheet = staticmethod(table_stylesheet)
    input_stylesheet = staticmethod(input_stylesheet)
    sidebar_stylesheet = staticmethod(sidebar_stylesheet)
    wizard_shell_stylesheet = staticmethod(wizard_shell_stylesheet)
    data_panel_stylesheet = staticmethod(data_panel_stylesheet)
    analytics_page_stylesheet = staticmethod(analytics_page_stylesheet)
    settings_panel_stylesheet = staticmethod(settings_panel_stylesheet)
    global_stylesheet = staticmethod(global_stylesheet)


Theme = ProjectXTheme
