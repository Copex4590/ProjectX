from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)


class ConnectionPanel(QFrame):

    def __init__(self):
        super().__init__()

        self.setFixedWidth(240)

        self.setStyleSheet("""
            QFrame{
                background:#252a31;
                border-left:1px solid #40444b;
            }

            QLabel{
                color:white;
                padding:6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Connections")
        title.setStyleSheet("""
            font-size:14pt;
            font-weight:bold;
        """)

        layout.addWidget(title)

        self.internet = QLabel("🟢 Internet")
        self.ais = QLabel("⚪ AISStream")
        self.rtl = QLabel("⚪ RTL Receiver")
        self.gps = QLabel("⚪ GPS")
        self.camera = QLabel("⚪ Camera")
        self.database = QLabel("⚪ Database")
        self.api = QLabel("⚪ API")

        layout.addWidget(self.internet)
        layout.addWidget(self.ais)
        layout.addWidget(self.rtl)
        layout.addWidget(self.gps)
        layout.addWidget(self.camera)
        layout.addWidget(self.database)
        layout.addWidget(self.api)

        layout.addStretch()

    def on_ais_status(self, status):

        if status == "connected":
            self.ais.setText("🟢 AISStream")
        elif status == "connecting":
            self.ais.setText("🟡 AISStream")
        else:
            self.ais.setText("⚪ AISStream")

    def on_rtl_status(self, status):

        if status == "connected":
            self.rtl.setText("🟢 RTL Receiver")
        elif status == "connecting":
            self.rtl.setText("🟡 RTL Receiver")
        else:
            self.rtl.setText("⚪ RTL Receiver")
