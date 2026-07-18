# ============================================================================
# Project X
# AIS Provider Coverage Notice (one-time UX)
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from gui.dont_show_again import create_dont_show_again_checkbox
from gui.i18n_support import bind_language_refresh
from gui.theme import TEXT, secondary_button_stylesheet, wizard_shell_stylesheet
from i18n import tr


class ProviderCoverageNoticeDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self._view_coverage_requested = False
        self.setModal(True)
        self.setMinimumWidth(520)

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def view_coverage_requested(self) -> bool:

        return self._view_coverage_requested

    def dont_show_again(self) -> bool:

        return self._dont_show_checkbox.isChecked()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Selecting an AIS provider"))
        self._title.setText(tr("Selecting an AIS provider"))
        self._body.setText(
            tr(
                "Each AIS provider has different geographic coverage.\n"
                "Service quality also depends on how many receiver stations "
                "operate in your area and what data the provider offers.\n"
                "We recommend checking coverage on the provider's website "
                "before requesting an API key or subscribing."
            )
        )
        self._view_coverage_button.setText(tr("View coverage"))
        self._continue_button.setText(tr("Continue"))
        self._dont_show_checkbox.setText(tr("Don't show again"))

    def _build_ui(self) -> None:

        self.setStyleSheet(wizard_shell_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        self._title = QLabel()
        self._title.setWordWrap(True)
        self._title.setStyleSheet("font-size: 14pt; font-weight: bold; color: white;")
        layout.addWidget(self._title)

        self._body = QLabel()
        self._body.setWordWrap(True)
        self._body.setStyleSheet(f"color: {TEXT}; font-size: 11pt;")
        layout.addWidget(self._body)

        self._dont_show_checkbox = create_dont_show_again_checkbox()
        layout.addWidget(self._dont_show_checkbox)

        layout.addSpacing(8)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._view_coverage_button = QPushButton()
        self._view_coverage_button.setStyleSheet(
            secondary_button_stylesheet(padding="8px 16px")
        )
        self._view_coverage_button.clicked.connect(self._on_view_coverage)
        button_row.addWidget(self._view_coverage_button)

        self._continue_button = QPushButton()
        self._continue_button.setStyleSheet(
            secondary_button_stylesheet(padding="8px 16px")
        )
        self._continue_button.setMinimumWidth(120)
        self._continue_button.clicked.connect(self.accept)
        button_row.addWidget(self._continue_button)

        layout.addLayout(button_row)

    def _on_view_coverage(self) -> None:

        self._view_coverage_requested = True
        self.accept()
