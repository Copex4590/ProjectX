# ============================================================================
# Project X
# "Don't show again" checkbox helper (UX policy)
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QWidget

from gui.theme import TEXT_MUTED
from i18n import tr


def create_dont_show_again_checkbox(parent: QWidget | None = None) -> QCheckBox:
    """Return an unchecked suppression checkbox.

    Project X UX policy: never pre-check "Don't show again". Suppressing future
    messages must be an explicit user choice.
    """

    checkbox = QCheckBox(tr("Don't show again"), parent)
    checkbox.setStyleSheet(f"color: {TEXT_MUTED};")
    return checkbox
