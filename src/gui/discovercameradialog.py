# ============================================================================
# Project X
# Discover Camera — camera page URL entry (Hunter in-process)
# ============================================================================

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QVBoxLayout,
)

from i18n import tr


class DiscoverCameraDialog(QDialog):
    """Ask for a direct camera page URL. Not a listing / mapsearch UI."""

    def __init__(self, parent=None):

        super().__init__(parent)
        self.setWindowTitle(tr("Discover Camera"))
        self.setModal(True)
        self.setMinimumWidth(420)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self._url = QLineEdit()
        self._url.setPlaceholderText("https://")
        form.addRow(tr("Camera page URL"), self._url)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def page_url(self) -> str:

        return self._url.text().strip()
