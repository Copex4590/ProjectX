from PySide6.QtWidgets import (
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
    QLabel,
)
from PySide6.QtCore import Qt, Signal

from database import registry
from events import eventbus


class VesselsPage(QWidget):

    shipSelected = Signal(int)

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

        self.list.itemClicked.connect(self.item_clicked)

        self._last_count = -1

        self.refresh()

        eventbus.subscribe(
            "ship.updated",
            self.ship_updated
        )

    def refresh(self):

        ships = sorted(
            registry.all(),
            key=lambda s: s.name.lower()
        )

        self._last_count = len(ships)

        self.list.clear()

        for ship in ships:

            item = QListWidgetItem(
                f"{ship.name:28} {ship.speed:5.1f} km/h"
            )

            item.setData(
                Qt.UserRole,
                ship.mmsi
            )

            self.list.addItem(item)

    def item_clicked(self, item):

        mmsi = item.data(Qt.UserRole)

        if mmsi is not None:
            self.shipSelected.emit(mmsi)

    def ship_updated(self, ship):

        self.refresh()
