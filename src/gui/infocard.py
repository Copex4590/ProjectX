from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout


class InfoCard(QFrame):

    def __init__(self, title, value):

        super().__init__()

        self.setMinimumHeight(120)

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

        layout.setContentsMargins(15, 15, 15, 15)

        caption = QLabel(title)

        caption.setStyleSheet("""
            color:#9aa4af;
            font-size:10pt;
        """)

        number = QLabel(value)

        number.setAlignment(Qt.AlignCenter)

        number.setStyleSheet("""
            font-size:24pt;
            font-weight:bold;
        """)

        layout.addWidget(caption)
        layout.addStretch()
        layout.addWidget(number)
        layout.addStretch()
