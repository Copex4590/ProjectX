from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from gui.settings.cameradiagnosticspanel import CameraDiagnosticsPanel
from gui.settings.playbacksettings import PlaybackSettingsPage


class SettingsPanel(QFrame):

    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QFrame{
                background:#353b44;
                border:1px solid #4b535d;
                border-radius:10px;
            }

            QLabel{
                color:white;
                font-size:14pt;
                font-weight:bold;
            }

            QCheckBox{
                color:white;
            }

            QComboBox{
                background:#252a31;
                color:white;
                border:1px solid #40444b;
                padding:4px;
            }

            QPushButton{
                background:#1976d2;
                color:white;
                border:none;
                padding:8px;
                border-radius:6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,15,15,15)

        layout.addWidget(QLabel("Quick Settings"))

        layout.addWidget(QCheckBox("Enable AIS"))
        layout.addWidget(QCheckBox("Enable RTL Receiver"))
        layout.addWidget(QCheckBox("Enable Cameras"))

        layout.addWidget(QLabel("Theme"))

        combo = QComboBox()
        combo.addItems(["Dark","Light"])

        layout.addWidget(combo)

        layout.addWidget(QPushButton("Save"))

        layout.addWidget(PlaybackSettingsPage())

        layout.addWidget(CameraDiagnosticsPanel())

        layout.addStretch()
