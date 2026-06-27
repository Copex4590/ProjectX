from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)


class AlertsPanel(QFrame):

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
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,15,15,15)

        title = QLabel("Alerts")

        title.setStyleSheet("""
            font-size:14pt;
            font-weight:bold;
        """)

        layout.addWidget(title)

        layout.addWidget(QLabel("✓ No active alerts"))
        layout.addStretch()
