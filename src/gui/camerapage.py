from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from gui.i18n_support import bind_language_refresh
from i18n import tr


class CameraPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self._title_label = QLabel(tr("Cameras"))
        self._title_label.setAlignment(Qt.AlignCenter)

        self._title_label.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)

        layout.addStretch()
        layout.addWidget(self._title_label)
        layout.addStretch()

        bind_language_refresh(self.refresh_translations)

    def refresh_translations(self) -> None:

        self._title_label.setText(tr("Cameras"))
