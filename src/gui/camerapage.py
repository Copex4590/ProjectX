from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout

from PySide6.QtCore import Qt

from gui.i18n_support import bind_language_refresh
from gui.widgets.emptystate import EmptyStateWidget
from i18n import tr


class CameraPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)

        self._title_label = QLabel(tr("Cameras"))
        self._title_label.setAlignment(Qt.AlignCenter)
        self._title_label.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)
        layout.addWidget(self._title_label)

        self._empty_state = EmptyStateWidget(
            "No cameras",
            help_title_key="Cameras help — title",
            help_body_key="Cameras help — body",
        )
        layout.addWidget(self._empty_state, 1)

        bind_language_refresh(self.refresh_translations)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Cameras"))
