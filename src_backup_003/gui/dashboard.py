from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QFrame,
    QLabel,
    QVBoxLayout,
)

from gui.toolbar import ToolBar
from gui.statisticspanel import StatisticsPanel
from gui.systempanel import SystemPanel
from gui.receiverpanel import ReceiverPanel
from gui.camerapanel import CameraPanel
from gui.vesselspanel import VesselsPanel
from gui.mappanel import MapPanel
from gui.alertspanel import AlertsPanel
from gui.notificationpanel import NotificationPanel
from gui.settingspanel import SettingsPanel
from gui.logpanel import LogPanel


class Dashboard(QFrame):

    def __init__(self):
        super().__init__()

        self.setStyleSheet("""
            QFrame{
                background:#2b2f36;
            }
        """)

        root = QVBoxLayout(self)
        root.setContentsMargins(0,0,0,0)
        root.setSpacing(0)

        root.addWidget(ToolBar())

        content = QWidget()

        layout = QVBoxLayout(content)
        layout.setContentsMargins(25,25,25,25)
        layout.setSpacing(20)

        title = QLabel("Dashboard")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            font-size:24pt;
            font-weight:bold;
        """)

        subtitle = QLabel("Project X is ready.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            color:#9aa4af;
            font-size:12pt;
        """)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        layout.addWidget(StatisticsPanel())
        layout.addWidget(SystemPanel())
        layout.addWidget(ReceiverPanel())
        layout.addWidget(CameraPanel())
        layout.addWidget(VesselsPanel())
        layout.addWidget(MapPanel())
        layout.addWidget(AlertsPanel())
        layout.addWidget(NotificationPanel())
        layout.addWidget(SettingsPanel())
        layout.addWidget(LogPanel())

        layout.addStretch()

        root.addWidget(content)
