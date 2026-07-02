from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from gui.sidebar import Sidebar
from gui.connectionpanel import ConnectionPanel
from gui.statuspanel import StatusPanel
from gui.menubar import MenuBar

from gui.dashboardpage import DashboardPage
from gui.mappage import MapPage
from gui.vesselspage import VesselsPage
from gui.camerapage import CameraPage

from engines.ais import AISStreamEngine


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project X")
        self.resize(1600, 900)

        self.ais_engine = AISStreamEngine()

        self.build_ui()

        print("🚢 AIS Engine indítása...")
        self.ais_engine.start()

    def build_ui(self):

        self.setMenuBar(MenuBar())

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.map_page = MapPage()
        self.vessels_page = VesselsPage()
        self.camera_page = CameraPage()

        self.pages.addWidget(self.dashboard_page)   # 0
        self.pages.addWidget(self.map_page)         # 1
        self.pages.addWidget(self.vessels_page)     # 2
        self.pages.addWidget(self.camera_page)      # 3

        self.sidebar = Sidebar()
        self.sidebar.pageSelected.connect(self.pages.setCurrentIndex)

        self.vessels_page.shipSelected.connect(
            self.focus_ship
        )

        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)
        root.addWidget(ConnectionPanel())

        self.setStatusBar(StatusPanel())

    def focus_ship(self, mmsi):

        self.pages.setCurrentIndex(1)

        self.map_page.map.focus_ship(mmsi)

    def closeEvent(self, event):

        print("🛑 AIS Engine leállítása...")

        self.ais_engine.stop()

        super().closeEvent(event)
