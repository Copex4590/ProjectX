from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout


class Sidebar(QFrame):

    def __init__(self):
        super().__init__()

        self.setFixedWidth(260)

        self.setStyleSheet("""
            QFrame{
                background:#1d2127;
                border-right:1px solid #40444b;
            }

            QLabel{
                color:white;
                padding:10px 12px;
                border-radius:6px;
            }

            QLabel:hover{
                background:#3b434d;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20,20,20,20)
        layout.setSpacing(8)

        logo = QLabel("PROJECT X")
        logo.setAlignment(Qt.AlignCenter)

        logo.setStyleSheet("""
            font-size:22pt;
            font-weight:bold;
            padding:20px;
        """)

        layout.addWidget(logo)

        menu = [
            "🏠 Dashboard",
            "🗺 Live Map",
            "🚢 Vessels",
            "📷 Cameras",
            "📡 AIS",
            "📻 RTL",
            "🛰 Receiver",
            "📈 Statistics",
            "🔔 Alerts",
            "⚙ Settings",
            "❓ Help"
        ]

        for text in menu:

            item = QLabel(text)
            item.setMinimumHeight(38)

            layout.addWidget(item)

        layout.addStretch()
