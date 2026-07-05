# ============================================================================
# Project X
# Wizard Help
# ============================================================================

from PySide6.QtWidgets import QDialogButtonBox, QMessageBox, QPushButton

from i18n import tr

_WIZARD_NAV_ROLE = QDialogButtonBox.ButtonRole.ActionRole


def add_wizard_back_button(button_box: QDialogButtonBox) -> QPushButton:
    """Qt6-compatible Back button (QDialogButtonBox.StandardButton.Back was removed)."""

    return button_box.addButton("", _WIZARD_NAV_ROLE)


def add_wizard_next_button(button_box: QDialogButtonBox) -> QPushButton:
    """Qt6-compatible Next button (QDialogButtonBox.StandardButton.Next was removed)."""

    return button_box.addButton("", _WIZARD_NAV_ROLE)


def show_wizard_help(parent, title_key: str, body_key: str) -> None:

    QMessageBox.information(
        parent,
        tr(title_key),
        tr(body_key),
    )
