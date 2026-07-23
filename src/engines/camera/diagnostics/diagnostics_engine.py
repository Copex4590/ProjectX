# ============================================================================
# Project X
# Camera Diagnostics Engine
# ============================================================================

from database.camera_registry import camera_registry
from engines.camera.diagnostics.diagnostics_result import (
    CameraDiagnosticsReport,
    DiagnosticResult,
    DiagnosticSeverity,
)
from models.camera import Camera
import logging

logger = logging.getLogger(__name__)

_KNOWN_PROVIDER_TYPES = frozenset({
    "hls",
    "m3u8",
    "rtsp",
    "snapshot",
    "image",
    "jpeg",
    "jpg",
    "png",
    "youtube",
})


class CameraDiagnosticsEngine:

    def __init__(self, registry=None):

        self._registry = registry or camera_registry

    def diagnose(
        self,
        camera: Camera,
        *,
        duplicate_ids: set[str] | None = None,
    ) -> CameraDiagnosticsReport:

        results = []

        results.extend(
            self._check_configuration(camera, duplicate_ids or set())
        )
        results.extend(self._check_playback(camera))
        results.extend(self._check_selection(camera))

        if not results:
            results.append(
                DiagnosticResult(
                    camera_id=camera.id,
                    severity=DiagnosticSeverity.OK,
                    message="Camera configuration is healthy.",
                    recommendation="No action required.",
                    category="summary",
                )
            )

        return CameraDiagnosticsReport(
            camera_id=camera.id,
            results=tuple(results),
        )

    def diagnose_all(self) -> list[CameraDiagnosticsReport]:

        cameras = self._registry.all()
        duplicate_ids = self._find_duplicate_ids(cameras)

        return [
            self.diagnose(camera, duplicate_ids=duplicate_ids)
            for camera in cameras
        ]

    def _find_duplicate_ids(self, cameras: list[Camera]) -> set[str]:

        seen: set[str] = set()
        duplicates: set[str] = set()

        for camera in cameras:
            camera_id = self._safe_text(camera.id)

            if not camera_id:
                continue

            if camera_id in seen:
                duplicates.add(camera_id)
            else:
                seen.add(camera_id)

        return duplicates

    def _check_configuration(
        self,
        camera: Camera,
        duplicate_ids: set[str],
    ) -> list[DiagnosticResult]:

        results = []
        camera_id = self._safe_text(camera.id) or "unknown"

        if not self._safe_text(camera.id):
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Camera id is missing.",
                    recommendation="Assign a unique camera id in the configuration file.",
                    category="configuration",
                )
            )
        elif camera.id in duplicate_ids:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message=f"Duplicate camera id detected: {camera.id}",
                    recommendation="Ensure every camera id is unique across all camera packs.",
                    category="configuration",
                )
            )

        if not self._safe_text(camera.name):
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Required field 'name' is missing.",
                    recommendation="Provide a descriptive camera name.",
                    category="configuration",
                )
            )

        if not self._safe_text(camera.country):
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Required field 'country' is missing.",
                    recommendation="Set the camera country code in the configuration.",
                    category="configuration",
                )
            )

        if not self._is_valid_latitude(camera.lat):
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Required field 'lat' is invalid.",
                    recommendation="Use a latitude between -90 and 90 degrees.",
                    category="configuration",
                )
            )

        if not self._is_valid_longitude(camera.lon):
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Required field 'lon' is invalid.",
                    recommendation="Use a longitude between -180 and 180 degrees.",
                    category="configuration",
                )
            )

        provider_type = camera.playback_provider_type

        if provider_type and provider_type not in _KNOWN_PROVIDER_TYPES:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.WARNING,
                    message=f"Unknown provider type '{provider_type}'.",
                    recommendation="Use a supported provider type such as hls, rtsp, snapshot, or youtube.",
                    category="configuration",
                )
            )

        if not camera.enabled:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.WARNING,
                    message="Camera is disabled.",
                    recommendation="Enable the camera when it should participate in selection and playback.",
                    category="configuration",
                )
            )

        return results

    def _check_playback(self, camera: Camera) -> list[DiagnosticResult]:

        from engines.camera.providers import provider_registry
        from engines.playback import backend_registry

        results = []
        camera_id = self._safe_text(camera.id) or "unknown"
        provider_type = camera.playback_provider_type
        stream_url = camera.playback_stream_url

        if provider_type and not stream_url:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Playback provider type is configured without a stream_url.",
                    recommendation="Add a valid stream_url for the selected provider type.",
                    category="playback",
                )
            )

        if stream_url and not provider_type:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.WARNING,
                    message="stream_url is configured without provider_type.",
                    recommendation="Set provider_type so the correct camera provider can be selected.",
                    category="playback",
                )
            )

        if not stream_url and not provider_type and not camera.has_playback_metadata():
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.WARNING,
                    message="Playback metadata is not configured.",
                    recommendation="Add provider_type and stream_url when live playback is required.",
                    category="playback",
                )
            )

        provider = provider_registry.get_provider(camera)

        if stream_url or provider_type:
            if provider is None:
                results.append(
                    DiagnosticResult(
                        camera_id=camera_id,
                        severity=DiagnosticSeverity.ERROR,
                        message="No camera provider supports this camera configuration.",
                        recommendation="Adjust provider_type or stream_url to match an installed provider.",
                        category="playback",
                    )
                )
            else:
                provider_session = None

                try:
                    provider_session = provider.open(camera)
                except Exception:
                    logger.exception(
                        "Camera provider open failed during diagnostics for %s",
                        camera_id,
                    )
                    provider_session = None

                if provider_session is None:
                    results.append(
                        DiagnosticResult(
                            camera_id=camera_id,
                            severity=DiagnosticSeverity.ERROR,
                            message="Camera provider could not prepare a provider session.",
                            recommendation="Verify stream_url and provider_type values for this camera.",
                            category="playback",
                        )
                    )
                else:
                    backend = backend_registry.get_backend(provider_session)

                    if backend is None:
                        results.append(
                            DiagnosticResult(
                                camera_id=camera_id,
                                severity=DiagnosticSeverity.ERROR,
                                message="No playback backend is available for this camera stream.",
                                recommendation="Register a compatible playback backend or update playback preferences.",
                                category="playback",
                            )
                        )
                    else:
                        results.append(
                            DiagnosticResult(
                                camera_id=camera_id,
                                severity=DiagnosticSeverity.OK,
                                message=(
                                    f"Playback provider '{provider.name}' and "
                                    f"backend '{backend.name}' are available."
                                ),
                                recommendation="No action required.",
                                category="playback",
                            )
                        )

                    try:
                        provider.close()
                    except Exception:
                        logger.exception(
                            "Failed to close camera provider during diagnostics"
                        )

        return results

    def _check_selection(self, camera: Camera) -> list[DiagnosticResult]:

        results = []
        camera_id = self._safe_text(camera.id) or "unknown"

        if not camera.enabled:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.WARNING,
                    message="Disabled cameras are excluded from automatic selection.",
                    recommendation="Enable the camera to allow vessel-based camera matching.",
                    category="selection",
                )
            )

        if camera.visibility_radius_km < 0.0:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Visibility radius is negative.",
                    recommendation="Set visibility_radius_km to a positive distance in kilometers.",
                    category="selection",
                )
            )
        elif camera.visibility_radius_km == 0.0:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.WARNING,
                    message="Visibility radius is zero.",
                    recommendation="Set visibility_radius_km so vessels can be matched to this camera.",
                    category="selection",
                )
            )

        if not self._is_valid_angle(camera.direction_deg):
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Camera direction is invalid.",
                    recommendation="Use direction_deg between 0 and 360 degrees.",
                    category="selection",
                )
            )

        if camera.fov_deg <= 0.0:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.ERROR,
                    message="Camera field of view is not positive.",
                    recommendation="Set fov_deg to a positive viewing angle.",
                    category="selection",
                )
            )
        elif camera.fov_deg > 360.0:
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.WARNING,
                    message="Camera field of view exceeds 360 degrees.",
                    recommendation="Use a realistic fov_deg value, typically between 30 and 180 degrees.",
                    category="selection",
                )
            )

        if (
            camera.enabled
            and camera.visibility_radius_km > 0.0
            and self._is_valid_angle(camera.direction_deg)
            and 0.0 < camera.fov_deg <= 360.0
        ):
            results.append(
                DiagnosticResult(
                    camera_id=camera_id,
                    severity=DiagnosticSeverity.OK,
                    message="Camera selection parameters are valid.",
                    recommendation="No action required.",
                    category="selection",
                )
            )

        return results

    @staticmethod
    def _safe_text(value: str) -> str:

        if value is None:
            return ""

        return str(value).strip()

    @staticmethod
    def _is_valid_latitude(value: float) -> bool:

        return -90.0 <= float(value) <= 90.0

    @staticmethod
    def _is_valid_longitude(value: float) -> bool:

        return -180.0 <= float(value) <= 180.0

    @staticmethod
    def _is_valid_angle(value: float) -> bool:

        return 0.0 <= float(value) <= 360.0


camera_diagnostics_engine = CameraDiagnosticsEngine()
