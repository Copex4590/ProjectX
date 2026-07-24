# ============================================================================
# Project X
# Connection loss / restore notice dialog (SAVE-235)
# ============================================================================

from __future__ import annotations

from PySide6.QtCore import Qt
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


class ConnectionNoticeDialog(QDialog):
    """Non-modal connection notice: body text, don't-show-again, Close only.

    No separate title line. Does not auto-close — the user must dismiss it.
    """

    def __init__(
        self,
        *,
        connection_id: str,
        connection_label: str,
        restored: bool,
        parent=None,
    ):
        super().__init__(parent)

        self._connection_id = connection_id
        self._connection_label = connection_label
        self._restored = restored

        self.setModal(False)
        self.setWindowModality(Qt.WindowModality.NonModal)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(420)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        self._build_ui()
        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()

    @property
    def connection_id(self) -> str:

        return self._connection_id

    def dont_show_again(self) -> bool:

        return self._dont_show_checkbox.isChecked()

    def refresh_translations(self) -> None:

        # Window title is intentionally blank — no separate headline.
        self.setWindowTitle("")
        self._body.setText(self._body_text())
        self._dont_show_checkbox.setText(tr("Don't show again"))
        self._close_button.setText(tr("Dismiss"))

    def _body_text(self) -> str:

        name = self._connection_label
        if self._restored:
            return tr("{name} connection restored.").replace("{name}", name)

        return (
            f"{tr('{name} connection lost.').replace('{name}', name)}\n"
            f"{tr('Project X will reconnect automatically.')}"
        )

    def _build_ui(self) -> None:

        self.setStyleSheet(wizard_shell_stylesheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        self._body = QLabel()
        self._body.setWordWrap(True)
        self._body.setStyleSheet(f"color: {TEXT}; font-size: 11pt;")
        layout.addWidget(self._body)

        self._dont_show_checkbox = create_dont_show_again_checkbox()
        layout.addWidget(self._dont_show_checkbox)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self._close_button = QPushButton()
        self._close_button.setStyleSheet(
            secondary_button_stylesheet(padding="8px 16px")
        )
        self._close_button.setMinimumWidth(100)
        self._close_button.clicked.connect(self.accept)
        button_row.addWidget(self._close_button)

        layout.addLayout(button_row)
