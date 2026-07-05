from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from branding.assets import app_icon
from gui.aboutdialog import AboutDialog
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
from gui.settingspage import SettingsPage
from gui.eventbridge import EventBridge
from camera import camera_manager
from gui.firstrunwizard import FirstRunWizard

from i18n import language_manager
from observation import observation_manager
from preferences import preferences_manager
from inspector.inspector import PROJECT_VERSION
from version import PROJECT_NAME
from engines.ais.ais_catcher_launcher import ensure_ais_catcher_ready
from engines.rtl.hybrid_engine import HybridEngine
from logbook import logbook_recorder
from ais import ais_manager


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{PROJECT_NAME} {PROJECT_VERSION}")
        self.setWindowIcon(app_icon())
        self.resize(1600, 900)

        self.hybrid_engine = HybridEngine()
        logbook_recorder.start()
        ais_manager.start()

        self.build_ui()

        self.event_bridge = EventBridge()
        self._connect_event_bridge()
        self._connect_observation()
        self._connect_cameras()

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
        self.event_bridge.ais_status.connect(
            self.dashboard_page.refresh_ais,
            connection,
        )
        self.event_bridge.rtl_status.connect(
            self.connection_panel.on_rtl_status,
            connection,
        )
        self.event_bridge.rtl_status.connect(
            self.dashboard_page.refresh_ais,
            connection,
        )

    def _connect_observation(self) -> None:

        connection = Qt.ConnectionType.QueuedConnection

        observation_manager.changed.connect(
            self.dashboard_page.refresh_observation,
            connection,
        )
        observation_manager.changed.connect(
            self.dashboard_page.refresh_cameras,
            connection,
        )
        observation_manager.changed.connect(
            self.map_page.on_observation_changed,
            connection,
        )

        if self._should_show_first_run_wizard():
            QTimer.singleShot(0, self._show_first_run_wizard)

    def _connect_cameras(self) -> None:

        connection = Qt.ConnectionType.QueuedConnection

        camera_manager.changed.connect(
            self.dashboard_page.refresh_cameras,
            connection,
        )

    def _should_show_first_run_wizard(self) -> bool:

        if observation_manager.all():
            preferences = preferences_manager.get()

            if not preferences.first_run_completed:
                preferences_manager.set_first_run_completed(True)

            return False

        preferences = preferences_manager.get()
        return not preferences.first_run_completed

    def _show_first_run_wizard(self) -> None:

        if not self._should_show_first_run_wizard():
            return

        wizard = FirstRunWizard(self)

        if wizard.exec() != FirstRunWizard.DialogCode.Accepted:
            return

        if wizard.open_camera_page:
            self.pages.setCurrentIndex(3)
        else:
            self.pages.setCurrentIndex(0)

    def build_ui(self):

        self.menu_bar = MenuBar()
        self.setMenuBar(self.menu_bar)
        self.menu_bar.about_requested.connect(self._show_about)

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
        self.settings_page = SettingsPage()

        self.pages.addWidget(self.dashboard_page)        # 0
        self.pages.addWidget(self.map_page)              # 1
        self.pages.addWidget(self.vessels_page)          # 2
        self.pages.addWidget(self.camera_page)           # 3
        self.pages.addWidget(self.vessel_database_page)  # 4
        self.pages.addWidget(self.vessel_timeline_page)  # 5
        self.pages.addWidget(self.statistics_page)       # 6
        self.pages.addWidget(self.alert_center_page)     # 7
        self.pages.addWidget(self.rules_page)            # 8
        self.pages.addWidget(self.settings_page)         # 9

        self.sidebar = Sidebar()
        self.sidebar.pageSelected.connect(self.pages.setCurrentIndex)

        self.settings_page.personalization_changed.connect(
            self._apply_personalization
        )
        language_manager.language_changed.connect(
            self._apply_personalization
        )

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

        self._apply_personalization()

    def _apply_personalization(self) -> None:

        self.map_page.apply_personalization()

        for page in (
            self.dashboard_page,
            self.vessels_page,
            self.camera_page,
            self.vessel_database_page,
            self.vessel_timeline_page,
            self.statistics_page,
            self.alert_center_page,
            self.rules_page,
            self.settings_page,
        ):
            refresh = getattr(page, "refresh_translations", None)

            if callable(refresh):
                refresh()

        connection_refresh = getattr(
            self.connection_panel,
            "refresh_translations",
            None,
        )

        if callable(connection_refresh):
            connection_refresh()

        menu_refresh = getattr(self.menuBar(), "refresh_translations", None)

        if callable(menu_refresh):
            menu_refresh()

        status_refresh = getattr(
            self.statusBar(),
            "refresh_translations",
            None,
        )

        if callable(status_refresh):
            status_refresh()

    def focus_ship(self, mmsi):

        self.pages.setCurrentIndex(1)

        self.map_page.select_vessel(mmsi)
        self.map_page.map.focus_ship(mmsi)

    def _show_about(self) -> None:

        dialog = AboutDialog(self)
        dialog.exec()

    def closeEvent(self, event):

        print("🛑 Hybrid Engine leállítása...")

        self.hybrid_engine.stop()

        super().closeEvent(event)
