# ============================================================================
# Project X
# Observation Point Workflow Notice (one-time UX)
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


class ObservationPointWorkflowNoticeDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setModal(True)
        self.setMinimumWidth(520)

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def dont_show_again(self) -> bool:

        return self._dont_show_checkbox.isChecked()

    def refresh_translations(self) -> None:

        self.setWindowTitle(tr("Observation Point Workflow"))
        self._title.setText(tr("Observation Point Workflow"))
        self._body.setText(
            tr(
                "The Edit and Delete actions always operate on the currently "
                "active Observation Point.\n"
                "To work with another Observation Point, first select it using "
                "the \"Select Observation Point\" button."
            )
        )
        self._dont_show_checkbox.setText(tr("Don't show again"))
        self._ok_button.setText(tr("OK"))

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

        self._ok_button = QPushButton()
        self._ok_button.setStyleSheet(secondary_button_stylesheet(padding="8px 16px"))
        self._ok_button.setMinimumWidth(120)
        self._ok_button.clicked.connect(self.accept)
        button_row.addWidget(self._ok_button)

        layout.addLayout(button_row)
