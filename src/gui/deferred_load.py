# ============================================================================
# Project X — Deferred loading helpers (SAVE-228 / SAVE-230)
# ============================================================================
"""Shared UI helpers for background page loads.

Heavy page data uses ``ProgressiveDataPipeline`` (SAVE-229). This module keeps
the compact loading label used by Timeline, Vessel Database, Statistics, and
Analytics.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget

from gui.theme import ThemeColors
from i18n import tr


def make_loading_label(parent: QWidget | None = None) -> QLabel:
    """Compact status line used while deferred/progressive data is loading."""

    label = QLabel(parent)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setStyleSheet(
        f"color: {ThemeColors.TextSecondary}; font-size: 10pt; padding: 4px;"
    )
    label.hide()
    label.setText(tr("Loading…"))
    return label
