from PySide6.QtWidgets import (
    QListWidget,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from PySide6.QtCore import Qt

from database import registry
from events import eventbus


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

        layout.addWidget(title)

        self.list = QListWidget()

        self.list.setStyleSheet("""
            QListWidget{
                background:#252a31;
                color:white;
                border:1px solid #40444b;
                font-size:12pt;
            }
        """)

        layout.addWidget(self.list)

        self.refresh()

        eventbus.subscribe(
            "ship.updated",
            self.ship_updated
        )

    def refresh(self):

        self.list.clear()

        ships = sorted(
            registry.all(),
            key=lambda s: s.name.lower()
        )

        for ship in ships:

            self.list.addItem(
                f"{ship.name:28} {ship.speed:5.1f} km/h"
            )

    def ship_updated(self, ship):

        self.refresh()
