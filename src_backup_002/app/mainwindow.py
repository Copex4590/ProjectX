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


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project X")
        self.resize(1600, 900)

        self.build_ui()

    def build_ui(self):

        self.setMenuBar(MenuBar())

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)

        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.pages = QStackedWidget()

        self.pages.addWidget(DashboardPage())
        self.pages.addWidget(MapPage())
        self.pages.addWidget(VesselsPage())
        self.pages.addWidget(CameraPage())

        root.addWidget(Sidebar())
        root.addWidget(self.pages, 1)
        root.addWidget(ConnectionPanel())

        self.setStatusBar(StatusPanel())
