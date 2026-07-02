from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import QTimer
from gui.widgets.mapwidget import MapWidget
from database import registry


class MapPage(QWidget):

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.map = MapWidget()
        layout.addWidget(self.map)

        # 🚢 frissítés timerrel (event system helyett)
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_ships)
        self.timer.start(1000)

    def update_ships(self):

        ships = registry.all()

        for ship in ships:

            self.map.page().runJavaScript(f"""
                updateShip(
                    {ship.mmsi},
                    {ship.lat},
                    {ship.lon},
                    {ship.heading or 0}
                );
            """)
