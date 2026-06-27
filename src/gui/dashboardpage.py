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
            font-size:28pt;
            font-weight:bold;
        """)

        layout.addWidget(self.title)
        layout.addWidget(self.value)


class DashboardPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setAlignment(Qt.AlignCenter)

        title.setStyleSheet("""
            font-size:26pt;
            font-weight:bold;
            color:white;
        """)

        layout.addWidget(title)

        grid = QGridLayout()

        self.ships = InfoCard("Ships")
        self.ais = InfoCard("AIS")
        self.last = InfoCard("Last Ship")

        self.ais.value.setText("CONNECTED")

        grid.addWidget(self.ships, 0, 0)
        grid.addWidget(self.ais, 0, 1)
        grid.addWidget(self.last, 0, 2)

        layout.addLayout(grid)
        layout.addStretch()

        self.update_dashboard()

        eventbus.subscribe(
            "ship.updated",
            self.ship_updated
        )

    def update_dashboard(self):

        ships = registry.all()

        self.ships.value.setText(str(len(ships)))

        if ships:
            self.last.value.setText(ships[-1].name)
        else:
            self.last.value.setText("--")

    def ship_updated(self, ship):

        self.ships.value.setText(
            str(registry.count())
        )

        self.last.value.setText(
            ship.name
        )
