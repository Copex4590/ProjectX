import logging

from PySide6.QtCore import Qt, QEventLoop, QSize, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QWidget,
)

from app.page_registry import PageRegistry, PageSpec
from app.window_geometry import (
    WindowManagementSettings,
    window_geometry_manager,
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
from gui.eventbridge import EventBridge
from gui.notifications import AisConnectionMonitor, notification_manager
from gui.providers import refresh_open_provider_windows
from cameras import camera_manager
from debug.obs_freeze_trace import trace_slot
from gui.firstrunwizard import FirstRunWizard

from i18n import language_manager, tr
from observation import observation_manager
from preferences import preferences_manager
from preferences.application_settings import (
    apply_runtime_settings,
    startup_page_index,
)
from plugins import plugin_manager
from version import PROJECT_VERSION
from version import PROJECT_NAME
from engines.rtl.hybrid_engine import HybridEngine
from logbook import logbook_recorder
from ais import ais_manager
from rtl import rtl_manager
from gui.aiswizard import AISWizard
from gui.rtlsdrdiagnosticsdialog import RTLSdrDiagnosticsDialog
from gui.rtlsdrwizard import RTLSdrWizard

logger = logging.getLogger(__name__)

# Fits 1366×768 work areas with chrome; Window Management may size larger.
_MAINWINDOW_MINIMUM_SIZE = QSize(800, 500)


class _FlexibleStackedWidget(QStackedWidget):
    """Host pages without letting their content drive MainWindow minimum size."""

    def minimumSizeHint(self) -> QSize:
        return QSize(0, 0)

    def sizeHint(self) -> QSize:
        current = self.currentWidget()
        if current is None:
            return QSize(400, 300)
        hint = current.sizeHint()
        return QSize(max(400, hint.width()), max(300, hint.height()))


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(f"{PROJECT_NAME} {PROJECT_VERSION}")
        self.setWindowIcon(app_icon())
        self.setMinimumSize(_MAINWINDOW_MINIMUM_SIZE)

        self.hybrid_engine = HybridEngine()
        logbook_recorder.start()
        ais_manager.start()
        rtl_manager.start()

        self._page_registry: PageRegistry | None = None
        self._map_controller_wired = False
        self._session_replay_bridge = None

        # Lazy page attributes (set by PageRegistry; None until first open).
        self.map_page = None
        self.vessels_page = None
        self.camera_page = None
        self.vessel_database_page = None
        self.vessel_timeline_page = None
        self.statistics_page = None
        self.alert_center_page = None
        self.rules_page = None
        self.system_health_page = None
        self.vessel_database_manager_page = None
        self.backup_manager_page = None
        self.application_settings_page = None
        self.installed_plugins_page = None
        self.analytics_dashboard_page = None
        self.session_recording_page = None

        self.build_ui()

        self._cancel_pick_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self._cancel_pick_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self._cancel_pick_shortcut.activated.connect(self._cancel_active_location_pick)

        self.event_bridge = EventBridge()
        notification_manager()
        self._ais_connection_monitor = AisConnectionMonitor(self.hybrid_engine, self)
        self._connect_event_bridge()
        self._connect_observation()
        self._connect_cameras()

        QTimer.singleShot(0, self._start_background_services)

    def _start_background_services(self) -> None:

        logger.info("Starting Hybrid Engine")
        self.hybrid_engine.start()

        try:
            from alerts import professional_alerts_engine
            from alerts.gui_bridge import install_alerts_gui_bridge

            install_alerts_gui_bridge(self)
            professional_alerts_engine.start()
        except Exception:
            logger.exception("Failed to start Professional Alerts Engine")

    def _sync_provider_runtime(self, *_args) -> None:

        self.hybrid_engine.sync_enabled_providers()

    def _call_loaded_page(self, attr_name: str, method_name: str, *args, **kwargs):
        """Invoke a page method only if that page has been materialized."""

        registry = self._page_registry
        if registry is None:
            return None

        page = registry.get_loaded(attr=attr_name)
        if page is None:
            return None

        method = getattr(page, method_name, None)
        if not callable(method):
            return None

        return method(*args, **kwargs)

    def _require_page(self, attr_name: str):
        assert self._page_registry is not None
        return self._page_registry.ensure_attr(attr_name)

    def show_page(self, index: int) -> None:
        """Ensure the page exists, then switch the stack to it."""

        assert self._page_registry is not None
        self._page_registry.ensure(index)
        self.pages.setCurrentIndex(index)

    def _connect_event_bridge(self):

        connection = Qt.ConnectionType.QueuedConnection

        self.event_bridge.ship_updated.connect(
            trace_slot(
                "MainWindow->VesselsPage.refresh",
                lambda: self._call_loaded_page("vessels_page", "refresh"),
            ),
            connection,
        )
        self.event_bridge.ship_updated.connect(
            trace_slot(
                "MainWindow->DashboardPage.on_ship_updated",
                self.dashboard_page.on_ship_updated,
            ),
            connection,
        )
        self.event_bridge.ship_updated.connect(
            trace_slot(
                "MainWindow->MapPage.on_ship_updated",
                lambda: self._call_loaded_page("map_page", "on_ship_updated"),
            ),
            connection,
        )
        self.event_bridge.ais_status.connect(
            self.connection_panel.on_ais_status,
            connection,
        )
        self.event_bridge.ais_status.connect(
            trace_slot(
                "MainWindow->AisConnectionMonitor.on_status",
                self._ais_connection_monitor.on_status,
            ),
            connection,
        )
        self.event_bridge.ais_status.connect(
            trace_slot(
                "MainWindow->DashboardPage.refresh_ais",
                self.dashboard_page.refresh_ais,
            ),
            connection,
        )
        self.event_bridge.rtl_status.connect(
            self.connection_panel.on_rtl_status,
            connection,
        )
        self.event_bridge.rtl_status.connect(
            trace_slot(
                "MainWindow->DashboardPage.refresh_ais(rtl)",
                self.dashboard_page.refresh_ais,
            ),
            connection,
        )
        self.event_bridge.rtl_status.connect(
            trace_slot(
                "MainWindow->DashboardPage.refresh_rtl",
                self.dashboard_page.refresh_rtl,
            ),
            connection,
        )
        self.event_bridge.providers_changed.connect(
            trace_slot(
                "MainWindow->HybridEngine.sync_enabled_providers",
                self._sync_provider_runtime,
            ),
            connection,
        )
        self.event_bridge.providers_changed.connect(
            trace_slot(
                "MainWindow->DashboardPage.refresh_ais(providers)",
                self.dashboard_page.refresh_ais,
            ),
            connection,
        )
        self.event_bridge.providers_changed.connect(
            trace_slot(
                "MainWindow->refresh_open_provider_windows",
                refresh_open_provider_windows,
            ),
            connection,
        )
        self.event_bridge.ais_status.connect(
            trace_slot(
                "MainWindow->refresh_open_provider_windows(ais)",
                refresh_open_provider_windows,
            ),
            connection,
        )
        self.event_bridge.rtl_status.connect(
            trace_slot(
                "MainWindow->refresh_open_provider_windows(rtl)",
                refresh_open_provider_windows,
            ),
            connection,
        )

    def _connect_observation(self) -> None:

        connection = Qt.ConnectionType.QueuedConnection

        observation_manager.changed.connect(
            trace_slot(
                "MainWindow->DashboardPage.refresh_observation",
                self.dashboard_page.refresh_observation,
            ),
            connection,
        )
        observation_manager.changed.connect(
            trace_slot(
                "MainWindow->HybridEngine.on_observation_changed",
                self.hybrid_engine.on_observation_changed,
            ),
            connection,
        )
        observation_manager.changed.connect(
            trace_slot(
                "MainWindow->MapPage.on_observation_changed",
                lambda: self._call_loaded_page(
                    "map_page",
                    "on_observation_changed",
                ),
            ),
            connection,
        )

    def run_first_run_wizard(self) -> None:

        if not self._should_show_first_run_wizard():
            return

        wizard = FirstRunWizard(self)
        wizard.setModal(False)
        wizard.setWindowModality(Qt.WindowModality.NonModal)

        self.navigate_to_map()
        QApplication.processEvents()

        loop = QEventLoop(self)
        wizard.finished.connect(loop.quit)
        wizard.start_setup()
        loop.exec()

        if wizard.result() != FirstRunWizard.DialogCode.Accepted:
            return

        self.show_page(0)

    def _connect_cameras(self) -> None:

        connection = Qt.ConnectionType.QueuedConnection

        camera_manager.changed.connect(
            trace_slot(
                "MainWindow->DashboardPage.refresh_cameras",
                self.dashboard_page.refresh_cameras,
            ),
            connection,
        )

    def _should_show_first_run_wizard(self) -> bool:

        if observation_manager.all():
            preferences = preferences_manager.get()

            if not preferences.first_run_completed:
                preferences_manager.set_first_run_completed(True)

            return False

        return True

    def build_ui(self):

        self.menu_bar = MenuBar()
        self.setMenuBar(self.menu_bar)
        self.menu_bar.about_requested.connect(self._show_about)
        self.menu_bar.exit_requested.connect(QApplication.instance().quit)
        self.menu_bar._dashboard_action.triggered.connect(
            lambda: self.show_page(0)
        )
        self.menu_bar._map_action.triggered.connect(self.navigate_to_map)
        self.menu_bar._settings_action.triggered.connect(
            self._open_settings_manager
        )

        central = QWidget()
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.pages = _FlexibleStackedWidget()
        self.pages.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        self._page_registry = PageRegistry(self, self.pages)
        self._register_pages()

        try:
            from session.bridge import SessionReplayBridge

            self._session_replay_bridge = SessionReplayBridge(self)
        except Exception:
            logger.exception("Session replay bridge failed to initialize")
            self._session_replay_bridge = None

        self.sidebar = Sidebar()
        self.sidebar.pageSelected.connect(self._on_page_selected)
        self.pages.currentChanged.connect(self.sidebar.set_active_page)

        self.dashboard_page.personalization_changed.connect(
            self._apply_personalization
        )
        language_manager.language_changed.connect(
            self._apply_personalization
        )

        root.addWidget(self.sidebar)
        root.addWidget(self.pages, 1)
        self.connection_panel = ConnectionPanel()
        root.addWidget(self.connection_panel)

        self.setStatusBar(StatusPanel())

        self._apply_personalization()
        apply_runtime_settings()
        try:
            plugin_manager.initialize()
        except Exception:
            logger.exception("Plugin framework failed to initialize")
        self._apply_startup_options()

    def _register_pages(self) -> None:

        registry = self._page_registry
        assert registry is not None

        registry.register(
            PageSpec(
                index=0,
                attr_name="dashboard_page",
                factory=DashboardPage,
                eager=True,
            )
        )
        registry.register(
            PageSpec(
                index=1,
                attr_name="map_page",
                factory=self._factory_map_page,
                binder=self._bind_map_page,
            )
        )
        registry.register(
            PageSpec(
                index=2,
                attr_name="vessels_page",
                factory=self._factory_vessels_page,
                binder=self._bind_vessels_page,
            )
        )
        registry.register(
            PageSpec(
                index=3,
                attr_name="camera_page",
                factory=self._factory_camera_page,
            )
        )
        registry.register(
            PageSpec(
                index=4,
                attr_name="vessel_database_page",
                factory=self._factory_vessel_database_page,
                binder=self._bind_vessel_database_page,
            )
        )
        registry.register(
            PageSpec(
                index=5,
                attr_name="vessel_timeline_page",
                factory=self._factory_vessel_timeline_page,
                binder=self._bind_vessel_timeline_page,
            )
        )
        registry.register(
            PageSpec(
                index=6,
                attr_name="statistics_page",
                factory=self._factory_statistics_page,
            )
        )
        registry.register(
            PageSpec(
                index=7,
                attr_name="alert_center_page",
                factory=self._factory_alert_center_page,
                binder=self._bind_alert_center_page,
            )
        )
        registry.register(
            PageSpec(
                index=8,
                attr_name="rules_page",
                factory=self._factory_rules_page,
            )
        )
        registry.register(
            PageSpec(
                index=9,
                attr_name="system_health_page",
                factory=self._factory_system_health_page,
                binder=self._bind_system_health_page,
            )
        )
        registry.register(
            PageSpec(
                index=10,
                attr_name="vessel_database_manager_page",
                factory=self._factory_vessel_database_manager_page,
            )
        )
        registry.register(
            PageSpec(
                index=11,
                attr_name="backup_manager_page",
                factory=self._factory_backup_manager_page,
            )
        )
        registry.register(
            PageSpec(
                index=12,
                attr_name="application_settings_page",
                factory=self._factory_application_settings_page,
            )
        )
        registry.register(
            PageSpec(
                index=13,
                attr_name="installed_plugins_page",
                factory=self._factory_installed_plugins_page,
            )
        )
        registry.register(
            PageSpec(
                index=14,
                attr_name="analytics_dashboard_page",
                factory=self._factory_analytics_dashboard_page,
            )
        )
        registry.register(
            PageSpec(
                index=15,
                attr_name="session_recording_page",
                factory=self._factory_session_recording_page,
                binder=self._bind_session_recording_page,
            )
        )

    # --- lazy factories (defer heavy module import until first open) ---

    @staticmethod
    def _factory_map_page():
        from gui.mappage import MapPage

        return MapPage()

    @staticmethod
    def _factory_vessels_page():
        from gui.vesselspage import VesselsPage

        return VesselsPage()

    @staticmethod
    def _factory_camera_page():
        from gui.camerapage import CameraPage

        return CameraPage()

    @staticmethod
    def _factory_vessel_database_page():
        from gui.vesseldatabasepage import VesselDatabasePage

        return VesselDatabasePage()

    @staticmethod
    def _factory_vessel_timeline_page():
        from gui.vesseltimelinepage import VesselTimelinePage

        return VesselTimelinePage()

    @staticmethod
    def _factory_statistics_page():
        from gui.statisticspage import StatisticsPage

        return StatisticsPage()

    @staticmethod
    def _factory_alert_center_page():
        from gui.alertcenterpage import AlertCenterPage

        return AlertCenterPage()

    @staticmethod
    def _factory_rules_page():
        from gui.rulespage import RulesPage

        return RulesPage()

    @staticmethod
    def _factory_system_health_page():
        from gui.systemhealthpage import SystemHealthPage

        return SystemHealthPage()

    @staticmethod
    def _factory_vessel_database_manager_page():
        from gui.vesseldatabasemanagerpage import VesselDatabaseManagerPage

        return VesselDatabaseManagerPage()

    @staticmethod
    def _factory_backup_manager_page():
        from gui.backupmanagerpage import BackupManagerPage

        return BackupManagerPage()

    @staticmethod
    def _factory_application_settings_page():
        from gui.applicationsettingsmanagerpage import ApplicationSettingsManagerPage

        return ApplicationSettingsManagerPage()

    @staticmethod
    def _factory_installed_plugins_page():
        from gui.installedpluginspage import InstalledPluginsPage

        return InstalledPluginsPage()

    @staticmethod
    def _factory_analytics_dashboard_page():
        from gui.analyticsdashboardpage import AnalyticsDashboardPage

        return AnalyticsDashboardPage()

    @staticmethod
    def _factory_session_recording_page():
        from gui.sessionrecordingpage import SessionRecordingPage

        return SessionRecordingPage()

    # --- first-open binders (signals / host wiring once per page) ---

    def _bind_map_page(self, page) -> None:

        if not self._map_controller_wired:
            MapController.instance().set_dialog_parent(self)
            MapController.instance().navigation_requested.connect(
                lambda _page_index: self.navigate_to_map(),
                Qt.ConnectionType.QueuedConnection,
            )
            self._map_controller_wired = True

        MapController.instance().maybe_prompt_reference_selection()

    def _bind_vessels_page(self, page) -> None:

        page.shipSelected.connect(self.focus_ship)

    def _bind_vessel_database_page(self, page) -> None:

        page.vesselSelected.connect(self.focus_ship)

    def _bind_vessel_timeline_page(self, page) -> None:

        page.vesselSelected.connect(self.focus_ship)

    def _bind_alert_center_page(self, page) -> None:

        page.vesselSelected.connect(self.focus_ship)

    def _bind_system_health_page(self, page) -> None:

        page.attach_hybrid_engine(self.hybrid_engine)
        self._connect_system_health(page)

    def _bind_session_recording_page(self, page) -> None:

        page.navigateToMapRequested.connect(self.navigate_to_map)

    def _on_page_selected(self, index: int) -> None:

        self.show_page(index)

    def _apply_personalization(self) -> None:

        self._call_loaded_page("map_page", "apply_personalization")

        pages = [self.dashboard_page]
        if self._page_registry is not None:
            pages.extend(self._page_registry.loaded_pages())

        seen: set[int] = set()
        for page in pages:
            ident = id(page)
            if ident in seen:
                continue
            seen.add(ident)
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

    def _connect_system_health(self, page=None) -> None:

        if page is None:
            page = self.system_health_page
        if page is None:
            return

        page.configureAisRequested.connect(self._open_ais_configure)
        page.testAisRequested.connect(self._test_ais_from_health)
        page.rtlSetupRequested.connect(self._open_rtl_setup)
        page.rtlDiagnosticsRequested.connect(self._open_rtl_diagnostics)
        page.openSettingsRequested.connect(self._open_settings_manager)
        page.openDashboardRequested.connect(lambda: self.show_page(0))
        page.openMapRequested.connect(self.navigate_to_map)
        page.cameraDiagnosticsRequested.connect(self._open_camera_diagnostics)

    def _open_settings_manager(self) -> None:

        self.show_page(12)
        reload = getattr(self.application_settings_page, "reload_from_preferences", None)
        if callable(reload):
            reload()

    def _apply_startup_options(self) -> None:

        preferences = preferences_manager.get()
        self.apply_startup_window_management(preferences=preferences)

        page_index = startup_page_index(preferences)
        if 0 <= page_index < self.pages.count():
            self.show_page(page_index)

    def apply_startup_window_management(self, preferences=None) -> None:
        """
        Detect the current monitor, validate geometry, apply Window Management.

        Showing the window remains the Application controller's responsibility.
        """

        if preferences is None:
            preferences = preferences_manager.get()

        plan = window_geometry_manager.plan_startup(
            WindowManagementSettings(
                start_maximized=preferences.startup_maximized,
                restore_last=preferences.window_restore_geometry,
                auto_fit=preferences.window_auto_fit,
                always_center=preferences.window_always_center,
                limit_to_monitor=preferences.window_limit_to_monitor,
                saved_geometry=preferences.window_geometry,
            ),
            self,
        )

        # Always place a monitor-validated normal geometry first.
        if plan.geometry is not None:
            self.setGeometry(plan.geometry)

        self._startup_plan_maximized = plan.maximized

    def startup_should_maximize(self) -> bool:

        return bool(getattr(self, "_startup_plan_maximized", False))

    def _persist_window_geometry(self) -> None:

        try:
            preferences = preferences_manager.get()
            if not preferences.window_restore_geometry:
                return

            geometry = window_geometry_manager.geometry_for_persist(
                self,
                limit_to_monitor=preferences.window_limit_to_monitor,
            )
            preferences.window_geometry = geometry
            preferences_manager.save(preferences)
        except Exception:
            logger.exception("Failed to persist main window geometry")

    def _open_dashboard_configuration(self) -> None:

        self.show_page(0)
        self.dashboard_page.open_configuration_section()

    def _open_ais_configure(self) -> None:

        self.show_page(0)
        wizard = AISWizard(self)

        if wizard.exec() == AISWizard.DialogCode.Accepted:
            self.dashboard_page.refresh_ais()

        self._call_loaded_page("system_health_page", "refresh")

    def _test_ais_from_health(self) -> None:

        self.show_page(0)
        result = ais_manager.test_current()

        if result.success:
            QMessageBox.information(
                self,
                tr("AIS Providers"),
                tr(result.message) if result.message else tr("Connection successful"),
            )
        else:
            QMessageBox.warning(
                self,
                tr("AIS Providers"),
                tr(result.message) if result.message else tr("AIS source is not configured yet."),
            )

        self.dashboard_page.refresh_ais()
        self._call_loaded_page("system_health_page", "refresh")

    def _open_rtl_setup(self) -> None:

        self.show_page(0)
        wizard = RTLSdrWizard(self)

        if wizard.exec() == RTLSdrWizard.DialogCode.Accepted:
            self.dashboard_page.refresh_rtl()
            self.dashboard_page.refresh_ais()

        self._call_loaded_page("system_health_page", "refresh")

    def _open_rtl_diagnostics(self) -> None:

        dialog = RTLSdrDiagnosticsDialog(self)
        dialog.exec()
        self._call_loaded_page("system_health_page", "refresh")

    def _open_camera_diagnostics(self) -> None:

        self.show_page(0)
        self.dashboard_page.open_configuration_section(focus_diagnostics=True)

    def navigate_to_map(self, *, focus_mmsi: int | None = None) -> None:

        if not self.isVisible():
            self.show()

        self.raise_()
        self.activateWindow()
        self.show_page(MAP_PAGE_INDEX)

        if focus_mmsi is not None:
            map_page = self._require_page("map_page")
            map_page.select_vessel(int(focus_mmsi))
            MapController.instance().focus_ship(int(focus_mmsi))

    def focus_ship(self, mmsi):

        self.navigate_to_map(focus_mmsi=int(mmsi))

    def _show_about(self) -> None:

        dialog = AboutDialog(self)
        dialog.exec()

    def _cancel_active_location_pick(self) -> None:

        if MapController._instance is None:
            return

        if MapController.instance().pick_mode() != PickMode.NONE:
            MapController.instance().cancel_pick_mode()

    def closeEvent(self, event):

        if MapController._instance is not None:
            if MapController.instance().pick_mode() != PickMode.NONE:
                MapController.instance().cancel_pick_mode(restore_host=False)
            MapController.release_application_modality()

        self._persist_window_geometry()

        logger.info("Stopping Hybrid Engine")

        try:
            bridge = getattr(self, "event_bridge", None)
            shutdown = getattr(bridge, "shutdown", None)
            if callable(shutdown):
                shutdown()
        except Exception:
            logger.exception("Failed while shutting down EventBridge")

        try:
            from database.vessel_sync import vessel_sync
            from engines.timeline.arrival_departure_engine import (
                arrival_departure_engine,
            )
            from timeline.timeline_recorder import timeline_recorder

            logbook_recorder.stop()
            vessel_sync.stop()
            timeline_recorder.stop()
            arrival_departure_engine.stop()
            from database.vessel_database_manager import vessel_database_manager

            vessel_database_manager.stop()
        except Exception:
            logger.exception("Failed while stopping background workers")

        try:
            from session.player import session_player

            if session_player.is_active:
                session_player.stop()
            if getattr(self, "_session_replay_bridge", None) is not None:
                self._session_replay_bridge.shutdown()
            self._call_loaded_page(
                "alert_center_page",
                "apply_session_replay_alerts",
                None,
            )
            if MapController._instance is not None:
                MapController.instance().clear_playback()
        except Exception:
            logger.exception("Failed while stopping session replay")

        try:
            from alerts import professional_alerts_engine
            from alerts.gui_bridge import shutdown_alerts_gui_bridge

            professional_alerts_engine.stop()
            shutdown_alerts_gui_bridge()
        except Exception:
            logger.exception("Failed while stopping Professional Alerts Engine")

        try:
            for attr in (
                "alert_center_page",
                "analytics_dashboard_page",
                "map_page",
                "statistics_page",
                "vessel_timeline_page",
                "vessel_database_page",
            ):
                page = getattr(self, attr, None)
                shutdown = getattr(page, "shutdown", None)
                if callable(shutdown):
                    shutdown()
        except Exception:
            logger.exception("Failed while shutting down live pages")

        try:
            ais_manager.stop()
            rtl_manager.stop()
        except Exception:
            logger.exception("Failed while stopping AIS/RTL managers")

        try:
            plugin_manager.shutdown()
        except Exception:
            logger.exception("Failed while shutting down plugins")

        self.hybrid_engine.stop()

        super().closeEvent(event)
