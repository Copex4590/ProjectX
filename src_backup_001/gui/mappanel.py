from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QVBoxLayout,
)


class MapPanel(QFrame):

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
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Live Map")

        title.setStyleSheet("""
            font-size:14pt;
            font-weight:bold;
        """)

        map_area = QLabel("Map Engine Placeholder")

        map_area.setAlignment(Qt.AlignCenter)

        map_area.setMinimumHeight(320)

        map_area.setStyleSheet("""
            background:#252a31;
            border:1px solid #40444b;
            border-radius:6px;
            font-size:16pt;
            color:#7fb8ff;
        """)

        layout.addWidget(title)
        layout.addWidget(map_area)
