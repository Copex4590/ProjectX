from PySide6.QtCore import Qt
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
from gui.vesseldatabasepage import VesselDatabasePage
from gui.vesseltimelinepage import VesselTimelinePage
from gui.statisticspage import StatisticsPage
from gui.alertcenterpage import AlertCenterPage
from gui.rulespage import RulesPage
from gui.eventbridge import EventBridge

from engines.ais.ais_catcher_launcher import ensure_ais_catcher_ready
from engines.rtl.hybrid_engine import HybridEngine


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Project X")
        self.resize(1600, 900)

        self.hybrid_engine = HybridEngine()

        self.build_ui()

        self.event_bridge = EventBridge()
        self._connect_event_bridge()

        if ensure_ais_catcher_ready():
            print("🚢 Hybrid Engine indítása...")
            self.hybrid_engine.start()
        else:
            print(
                "⚠️ AIS-catcher nem elérhető – "
                "Hybrid Engine nem indul."
            )

    def _connect_event_bridge(self):

        connection = Qt.ConnectionType.QueuedConnection

        self.event_bridge.ship_updated.connect(
            self.vessels_page.refresh,
            connection,
        )
        self.event_bridge.ship_updated.connect(
            self.dashboard_page.on_ship_updated,
            connection,
        )
        self.event_bridge.ais_status.connect(
            self.connection_panel.on_ais_status,
            connection,
        )
        self.event_bridge.rtl_status.connect(
            self.connection_panel.on_rtl_status,
            connection,
        )

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
        self.vessel_database_page = VesselDatabasePage()
        self.vessel_timeline_page = VesselTimelinePage()
        self.statistics_page = StatisticsPage()
        self.alert_center_page = AlertCenterPage()
        self.rules_page = RulesPage()

        self.pages.addWidget(self.dashboard_page)        # 0
        self.pages.addWidget(self.map_page)              # 1
        self.pages.addWidget(self.vessels_page)          # 2
        self.pages.addWidget(self.camera_page)           # 3
        self.pages.addWidget(self.vessel_database_page)  # 4
        self.pages.addWidget(self.vessel_timeline_page)  # 5
        self.pages.addWidget(self.statistics_page)       # 6
        self.pages.addWidget(self.alert_center_page)     # 7
        self.pages.addWidget(self.rules_page)            # 8

        self.sidebar = Sidebar()
        self.sidebar.pageSelected.connect(self.pages.setCurrentIndex)

        self.vessels_page.shipSelected.connect(
            self.focus_ship
        )
        self.vessel_database_page.vesselSelected.connect(
            self.focus_ship
        )
        self.vessel_timeline_page.vesselSelected.connect(
            self.focus_ship
        )
        self.alert_center_page.vesselSelected.connect(
            self.focus_ship
        )

        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)
        self.connection_panel = ConnectionPanel()
        root.addWidget(self.connection_panel)

        self.setStatusBar(StatusPanel())

    def focus_ship(self, mmsi):

        self.pages.setCurrentIndex(1)

        self.map_page.select_vessel(mmsi)
        self.map_page.map.focus_ship(mmsi)

    def closeEvent(self, event):

        print("🛑 Hybrid Engine leállítása...")

        self.hybrid_engine.stop()

        super().closeEvent(event)
