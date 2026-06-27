from PySide6.QtWidgets import (
    QFrame,
    QTextEdit,
    QVBoxLayout,
    QLabel,
)


class LogPanel(QFrame):

    def __init__(self):
        super().__init__()

        self.setMinimumHeight(180)

        self.setStyleSheet("""
            QFrame{
                background:#353b44;
                border:1px solid #4b535d;
                border-radius:10px;
            }

            QLabel{
                color:white;
                font-size:13pt;
                font-weight:bold;
            }

            QTextEdit{
                background:#252a31;
                color:#d8d8d8;
                border:1px solid #40444b;
                border-radius:6px;
                font-family:monospace;
                font-size:10pt;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("System Log")

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.log.append("Project X started.")
        self.log.append("GUI initialized.")
        self.log.append("Waiting for modules...")

        layout.addWidget(title)
        layout.addWidget(self.log)
