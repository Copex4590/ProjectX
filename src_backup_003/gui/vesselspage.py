from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class VesselsPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Vessels")
        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)

        layout.addStretch()
        layout.addWidget(title)
        layout.addStretch()
