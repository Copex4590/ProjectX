# ============================================================================
# Project X
# Wizard Help
# ============================================================================

from PySide6.QtWidgets import QMessageBox

from i18n import tr


def show_wizard_help(parent, title_key: str, body_key: str) -> None:

    QMessageBox.information(
        parent,
        tr(title_key),
        tr(body_key),
    )
