from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QVBoxLayout,
)


class NotificationPanel(QFrame):

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

            QListWidget{
                background:#252a31;
                color:white;
                border:1px solid #40444b;
                border-radius:6px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15,15,15,15)

        layout.addWidget(QLabel("Notifications"))

        self.list = QListWidget()

        self.list.addItem("Project X started.")
        self.list.addItem("GUI initialized.")
        self.list.addItem("Waiting for AIS...")

        layout.addWidget(self.list)
