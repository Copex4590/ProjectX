from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from database import registry
from events import eventbus
from gui.widgets.mapwidget import MapWidget


class InfoCard(QFrame):

    def __init__(self, title):

        super().__init__()

        self.setStyleSheet("""
            QFrame{
                background:#252a31;
                border:1px solid #40444b;
                border-radius:10px;
            }
        """)

        layout = QVBoxLayout(self)

        self.title = QLabel(title)
        self.title.setAlignment(Qt.AlignCenter)

        self.title.setStyleSheet("""
            color:#bbbbbb;
            font-size:12pt;
        """)

        self.value = QLabel("--")
        self.value.setAlignment(Qt.AlignCenter)

        self.value.setStyleSheet("""
            color:white;
            font-size:22pt;
            font-weight:bold;
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.value)


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

        layout.addWidget(title)

        self.map = MapWidget()

        layout.addWidget(self.map, 1)

        info = QGridLayout()

        self.ship_count = InfoCard("Ships")
        self.last_update = InfoCard("Last Update")

        info.addWidget(self.ship_count, 0, 0)
        info.addWidget(self.last_update, 0, 1)

        layout.addLayout(info)

        self.refresh()

        eventbus.subscribe(
            "ship.updated",
            self.ship_updated
        )

    def refresh(self):

        self.ship_count.value.setText(
            str(registry.count())
        )

        self.last_update.value.setText(
            datetime.now().strftime("%H:%M:%S")
        )

    def ship_updated(self, ship):

        self.refresh()

        self.map.add_ship(ship)
