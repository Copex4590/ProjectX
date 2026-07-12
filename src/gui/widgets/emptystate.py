# ============================================================================
# Project X
# Empty State Widget
# ============================================================================

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from gui.i18n_support import bind_language_refresh
from gui.wizardhelp import show_wizard_help
from i18n import tr


class EmptyStateWidget(QWidget):

    helpRequested = Signal()

    def __init__(
        self,
        message_key: str,
        *,
        help_title_key: str = "",
        help_body_key: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self._message_key = message_key
        self._help_title_key = help_title_key
        self._help_body_key = help_body_key

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._message_label = QLabel()
        self._message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message_label.setWordWrap(True)
        self._message_label.setStyleSheet(
            "color: #9aa4af; font-size: 12pt;"
        )
        layout.addWidget(self._message_label)

        self._help_button = QPushButton()
        self._help_button.setStyleSheet("""
            QPushButton {
                background: #243651;
                color: white;
                border: 1px solid #2d5a8e;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background: #2d4a6f;
            }
        """)
        self._help_button.clicked.connect(self._on_help_clicked)
        layout.addWidget(self._help_button, alignment=Qt.AlignmentFlag.AlignCenter)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    def refresh_translations(self) -> None:

        self._message_label.setText(tr(self._message_key))
        self._help_button.setText(tr("Help"))
        self._help_button.setVisible(
            bool(self._help_title_key and self._help_body_key)
        )

    def _on_help_clicked(self) -> None:

        if self._help_title_key and self._help_body_key:
            show_wizard_help(
                self,
                self._help_title_key,
                self._help_body_key,
            )

        self.helpRequested.emit()
