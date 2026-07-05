# ============================================================================
# Project X
# Inspector
# ============================================================================

from cameras import camera_manager
from database import camera_registry, registry
from engines.camera.diagnostics import camera_diagnostics_engine
from engines.camera.providers import provider_registry
from engines.playback import backend_registry
from inspector.component_status import ComponentHealth, ComponentStatus
from inspector.health_report import HealthReport
from version import PROJECT_VERSION


class Inspector:

    def __init__(self, hybrid_engine=None):

        self._hybrid_engine = hybrid_engine

    def attach_hybrid_engine(self, hybrid_engine):

        self._hybrid_engine = hybrid_engine

    def get_system_report(
        self,
        *,
        hybrid_engine=None,
    ) -> HealthReport:

        engine = hybrid_engine if hybrid_engine is not None else self._hybrid_engine

        components = [
            self._inspect_hybrid_engine(engine),
            self._inspect_ship_registry(),
            self._inspect_camera_manager(),
            self._inspect_camera_packs(),
            self._inspect_camera_diagnostics(),
            self._inspect_playback_framework(),
            self._inspect_backend_registry(),
            self._inspect_provider_registry(),
        ]

        return HealthReport.from_components(components)

    def _inspect_hybrid_engine(self, engine) -> ComponentHealth:

        if engine is None:
            return ComponentHealth(
                name="HybridEngine",
                status=ComponentStatus.UNKNOWN,
                message="Hybrid engine instance is not attached to the inspector.",
                version=PROJECT_VERSION,
            )

        if getattr(engine, "running", False):
            return ComponentHealth(
                name="HybridEngine",
                status=ComponentStatus.OK,
                message="Hybrid engine is running.",
                version=PROJECT_VERSION,
            )

        return ComponentHealth(
            name="HybridEngine",
            status=ComponentStatus.WARNING,
            message="Hybrid engine is available but not running.",
            version=PROJECT_VERSION,
        )

    def _inspect_ship_registry(self) -> ComponentHealth:

        try:
            ship_count = registry.count()
        except Exception as error:
            return ComponentHealth(
                name="ShipRegistry",
                status=ComponentStatus.ERROR,
                message=f"Ship registry is unavailable: {error}",
            )

        return ComponentHealth(
            name="ShipRegistry",
            status=ComponentStatus.OK,
            message=f"Tracking {ship_count} vessel(s).",
        )

    def _inspect_camera_manager(self) -> ComponentHealth:

        try:
            camera_count = camera_manager.count()
            country_count = len(camera_manager.countries())
        except Exception as error:
            return ComponentHealth(
                name="CameraManager",
                status=ComponentStatus.ERROR,
                message=f"Camera manager is unavailable: {error}",
            )

        if camera_count == 0:
            return ComponentHealth(
                name="CameraManager",
                status=ComponentStatus.WARNING,
                message="Camera manager is active but no cameras are loaded.",
            )

        return ComponentHealth(
            name="CameraManager",
            status=ComponentStatus.OK,
            message=(
                f"Managing {camera_count} camera(s) "
                f"across {country_count} country pack(s)."
            ),
        )

    def _inspect_camera_packs(self) -> ComponentHealth:

        try:
            countries = camera_manager.countries()
            camera_count = camera_registry.count()
        except Exception as error:
            return ComponentHealth(
                name="Camera Packs",
                status=ComponentStatus.ERROR,
                message=f"Camera pack registry is unavailable: {error}",
            )

        if not countries:
            return ComponentHealth(
                name="Camera Packs",
                status=ComponentStatus.WARNING,
                message="No camera packs are loaded.",
            )

        country_summary = ", ".join(countries)

        return ComponentHealth(
            name="Camera Packs",
            status=ComponentStatus.OK,
            message=(
                f"Loaded {camera_count} camera(s) "
                f"from packs: {country_summary}."
            ),
        )

    def _inspect_camera_diagnostics(self) -> ComponentHealth:

        try:
            reports = camera_diagnostics_engine.diagnose_all()
        except Exception as error:
            return ComponentHealth(
                name="Camera Diagnostics",
                status=ComponentStatus.ERROR,
                message=f"Camera diagnostics failed: {error}",
            )

        if not reports:
            return ComponentHealth(
                name="Camera Diagnostics",
                status=ComponentStatus.WARNING,
                message="No cameras are available for diagnostics.",
            )

        error_count = sum(len(report.errors) for report in reports)
        warning_count = sum(len(report.warnings) for report in reports)

        if error_count:
            return ComponentHealth(
                name="Camera Diagnostics",
                status=ComponentStatus.ERROR,
                message=(
                    f"Detected {error_count} diagnostic error(s) "
                    f"across {len(reports)} camera(s)."
                ),
            )

        if warning_count:
            return ComponentHealth(
                name="Camera Diagnostics",
                status=ComponentStatus.WARNING,
                message=(
                    f"Detected {warning_count} diagnostic warning(s) "
                    f"across {len(reports)} camera(s)."
                ),
            )

        return ComponentHealth(
            name="Camera Diagnostics",
            status=ComponentStatus.OK,
            message=f"All {len(reports)} camera(s) passed diagnostics.",
        )

    def _inspect_playback_framework(self) -> ComponentHealth:

        try:
            backend_count = backend_registry.count()
            provider_count = provider_registry.count()
        except Exception as error:
            return ComponentHealth(
                name="Playback Framework",
                status=ComponentStatus.ERROR,
                message=f"Playback framework is unavailable: {error}",
            )

        if backend_count == 0:
            return ComponentHealth(
                name="Playback Framework",
                status=ComponentStatus.ERROR,
                message="Playback framework has no registered backends.",
            )

        if provider_count == 0:
            return ComponentHealth(
                name="Playback Framework",
                status=ComponentStatus.WARNING,
                message="Playback framework is active but no providers are registered.",
            )

        return ComponentHealth(
            name="Playback Framework",
            status=ComponentStatus.OK,
            message=(
                f"Playback framework ready with {provider_count} provider(s) "
                f"and {backend_count} backend(s)."
            ),
            version=PROJECT_VERSION,
        )

    def _inspect_backend_registry(self) -> ComponentHealth:

        try:
            backends = backend_registry.available_backends()
        except Exception as error:
            return ComponentHealth(
                name="Backend Registry",
                status=ComponentStatus.ERROR,
                message=f"Backend registry is unavailable: {error}",
            )

        if not backends:
            return ComponentHealth(
                name="Backend Registry",
                status=ComponentStatus.ERROR,
                message="No playback backends are registered.",
            )

        backend_names = ", ".join(backend.name for backend in backends)

        return ComponentHealth(
            name="Backend Registry",
            status=ComponentStatus.OK,
            message=f"Registered backends: {backend_names}.",
        )

    def _inspect_provider_registry(self) -> ComponentHealth:

        try:
            providers = provider_registry.list_providers()
        except Exception as error:
            return ComponentHealth(
                name="Provider Registry",
                status=ComponentStatus.ERROR,
                message=f"Provider registry is unavailable: {error}",
            )

        if not providers:
            return ComponentHealth(
                name="Provider Registry",
                status=ComponentStatus.ERROR,
                message="No camera providers are registered.",
            )

        provider_names = ", ".join(provider.name for provider in providers)

        return ComponentHealth(
            name="Provider Registry",
            status=ComponentStatus.OK,
            message=f"Registered providers: {provider_names}.",
        )


inspector = Inspector()
