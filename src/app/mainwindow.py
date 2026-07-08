import logging

from PySide6.QtCore import Qt, QEventLoop
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
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
from gui.mapcontroller import MapController
from gui.map_core import MAP_PAGE_INDEX, PickMode
from gui.mappage import MapPage
from gui.vesselspage import VesselsPage
from gui.camerapage import CameraPage
from gui.vesseldatabasepage import VesselDatabasePage
from gui.vesseltimelinepage import VesselTimelinePage
from gui.statisticspage import StatisticsPage
from gui.alertcenterpage import AlertCenterPage
from gui.rulespage import RulesPage
from gui.systemhealthpage import SystemHealthPage
from gui.eventbridge import EventBridge
from camera import camera_manager
from gui.firstrunwizard import FirstRunWizard

from i18n import language_manager, tr
from observation import observation_manager
from preferences import preferences_manager
from inspector.inspector import PROJECT_VERSION
from version import PROJECT_NAME
from engines.ais.ais_catcher_launcher import ensure_ais_catcher_ready
from engines.rtl.hybrid_engine import HybridEngine
from logbook import logbook_recorder
from ais import ais_manager
from rtl import rtl_manager
from gui.aiswizard import AISWizard
from gui.rtlsdrdiagnosticsdialog import RTLSdrDiagnosticsDialog
from gui.rtlsdrwizard import RTLSdrWizard

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{PROJECT_NAME} {PROJECT_VERSION}")
        self.setWindowIcon(app_icon())
        self.resize(1600, 900)

        self.hybrid_engine = HybridEngine()
        logbook_recorder.start()
        ais_manager.start()
        rtl_manager.start()

        self.build_ui()

        self._cancel_pick_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._cancel_pick_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._cancel_pick_shortcut.activated.connect(self._cancel_active_location_pick)

        self.event_bridge = EventBridge()
        self._connect_event_bridge()
        self._connect_observation()
        self._connect_cameras()

        if ensure_ais_catcher_ready():
            logger.info("Starting Hybrid Engine")
            self.hybrid_engine.start()
        else:
            logger.warning(
                "AIS-Catcher unavailable — Hybrid Engine not started"
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
        self.event_bridge.rtl_status.connect(
            self.dashboard_page.refresh_rtl,
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

    def run_first_run_wizard(self) -> None:

        if not self._should_show_first_run_wizard():
            return

        wizard = FirstRunWizard(self)
        wizard.setModal(False)
        wizard.setWindowModality(Qt.WindowModality.NonModal)

        loop = QEventLoop(self)
        wizard.finished.connect(loop.quit)
        wizard.show()
        loop.exec()

        if wizard.result() != FirstRunWizard.DialogCode.Accepted:
            return

        if wizard.open_camera_page:
            self.pages.setCurrentIndex(3)
        else:
            self.pages.setCurrentIndex(0)

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

    def build_ui(self):

        self.menu_bar = MenuBar()
        self.setMenuBar(self.menu_bar)
        self.menu_bar.about_requested.connect(self._show_about)
        self.menu_bar._dashboard_action.triggered.connect(
            lambda: self.pages.setCurrentIndex(0)
        )
        self.menu_bar._map_action.triggered.connect(self.navigate_to_map)
        self.menu_bar._settings_action.triggered.connect(
            self._open_dashboard_configuration
        )

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage()
        self.map_page = MapPage()
        MapController.instance().set_dialog_parent(self)
        MapController.instance().navigation_requested.connect(
            lambda _page_index: self.navigate_to_map(),
            Qt.ConnectionType.QueuedConnection,
        )
        self.vessels_page = VesselsPage()
        self.camera_page = CameraPage()
        self.vessel_database_page = VesselDatabasePage()
        self.vessel_timeline_page = VesselTimelinePage()
        self.statistics_page = StatisticsPage()
        self.alert_center_page = AlertCenterPage()
        self.rules_page = RulesPage()
        self.system_health_page = SystemHealthPage()

        self.pages.addWidget(self.dashboard_page)        # 0
        self.pages.addWidget(self.map_page)              # 1
        self.pages.addWidget(self.vessels_page)          # 2
        self.pages.addWidget(self.camera_page)           # 3
        self.pages.addWidget(self.vessel_database_page)  # 4
        self.pages.addWidget(self.vessel_timeline_page)  # 5
        self.pages.addWidget(self.statistics_page)       # 6
        self.pages.addWidget(self.alert_center_page)     # 7
        self.pages.addWidget(self.rules_page)            # 8
        self.pages.addWidget(self.system_health_page)    # 9

        self.system_health_page.attach_hybrid_engine(self.hybrid_engine)

        self.sidebar = Sidebar()
        self.sidebar.pageSelected.connect(self._on_page_selected)
        self.pages.currentChanged.connect(self.sidebar.set_active_page)

        self.dashboard_page.personalization_changed.connect(
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

        self._connect_system_health()

        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)
        self.connection_panel = ConnectionPanel()
        root.addWidget(self.connection_panel)

        self.setStatusBar(StatusPanel())

        self._apply_personalization()

        MapController.instance().maybe_prompt_reference_selection()

    def _on_page_selected(self, index: int) -> None:

        self.pages.setCurrentIndex(index)

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
            self.system_health_page,
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

    def _connect_system_health(self) -> None:

        page = self.system_health_page

        page.configureAisRequested.connect(self._open_ais_configure)
        page.testAisRequested.connect(self._test_ais_from_health)
        page.rtlSetupRequested.connect(self._open_rtl_setup)
        page.rtlDiagnosticsRequested.connect(self._open_rtl_diagnostics)
        page.openSettingsRequested.connect(self._open_dashboard_configuration)
        page.openDashboardRequested.connect(lambda: self.pages.setCurrentIndex(0))
        page.openMapRequested.connect(self.navigate_to_map)
        page.cameraDiagnosticsRequested.connect(self._open_camera_diagnostics)

    def _open_dashboard_configuration(self) -> None:

        self.pages.setCurrentIndex(0)
        self.dashboard_page.open_configuration_section()

    def _open_ais_configure(self) -> None:

        self.pages.setCurrentIndex(0)
        wizard = AISWizard(self)

        if wizard.exec() == AISWizard.DialogCode.Accepted:
            self.dashboard_page.refresh_ais()

        self.system_health_page.refresh()

    def _test_ais_from_health(self) -> None:

        self.pages.setCurrentIndex(0)
        result = ais_manager.test_current()

        if result.success:
            QMessageBox.information(
                self,
                tr("AIS Source"),
                tr(result.message) if result.message else tr("Connection successful"),
            )
        else:
            QMessageBox.warning(
                self,
                tr("AIS Source"),
                tr(result.message) if result.message else tr("AIS source is not configured yet."),
            )

        self.dashboard_page.refresh_ais()
        self.system_health_page.refresh()

    def _open_rtl_setup(self) -> None:

        self.pages.setCurrentIndex(0)
        wizard = RTLSdrWizard(self)

        if wizard.exec() == RTLSdrWizard.DialogCode.Accepted:
            self.dashboard_page.refresh_rtl()
            self.dashboard_page.refresh_ais()

        self.system_health_page.refresh()

    def _open_rtl_diagnostics(self) -> None:

        dialog = RTLSdrDiagnosticsDialog(self)
        dialog.exec()
        self.system_health_page.refresh()

    def _open_camera_diagnostics(self) -> None:

        self.pages.setCurrentIndex(0)
        self.dashboard_page.open_configuration_section(focus_diagnostics=True)

    def navigate_to_map(self, *, focus_mmsi: int | None = None) -> None:

        if not self.isVisible():
            self.show()

        self.raise_()
        self.activateWindow()
        self.pages.setCurrentIndex(MAP_PAGE_INDEX)

        if focus_mmsi is not None:
            self.map_page.select_vessel(int(focus_mmsi))
            MapController.instance().focus_ship(int(focus_mmsi))

    def focus_ship(self, mmsi):

        self.navigate_to_map(focus_mmsi=int(mmsi))

    def _show_about(self) -> None:

        dialog = AboutDialog(self)
        dialog.exec()

    def _cancel_active_location_pick(self) -> None:

        if MapController.instance().pick_mode() != PickMode.NONE:
            MapController.instance().cancel_pick_mode()

    def closeEvent(self, event):

        if MapController.instance().pick_mode() != PickMode.NONE:
            MapController.instance().cancel_pick_mode(restore_host=False)

        MapController.release_application_modality()

        logger.info("Stopping Hybrid Engine")
        self.hybrid_engine.stop()

        super().closeEvent(event)
