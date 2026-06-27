from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt


class MapPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Live Map")
        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)

        layout.addStretch()
        layout.addWidget(title)
        layout.addStretch()
