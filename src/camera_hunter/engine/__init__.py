from __future__ import annotations

from camera_hunter.engine.classifier import ObservedRequest, merge_observations
from camera_hunter.engine.discovery import DiscoveryEngine, DiscoveryResult
from camera_hunter.engine.hls_capture import (
    HlsCaptureResult,
    capture_hls,
    select_hls_url,
)
from camera_hunter.engine.session import (
    CAMERA_ACTIVATION_DELAY_SEC,
    DEFAULT_MAPSEARCH_URL,
    HEALTH_CHECK_INTERVAL_SEC,
    HunterSession,
    HunterState,
)
from camera_hunter.models import (
    CameraResult,
    CameraResultType,
    camera_result_from_source,
    camera_result_from_sources,
)

__all__ = [
    "CAMERA_ACTIVATION_DELAY_SEC",
    "DEFAULT_MAPSEARCH_URL",
    "HEALTH_CHECK_INTERVAL_SEC",
    "CameraResult",
    "CameraResultType",
    "DiscoveryEngine",
    "DiscoveryResult",
    "HlsCaptureResult",
    "HunterSession",
    "HunterState",
    "ObservedRequest",
    "camera_result_from_source",
    "camera_result_from_sources",
    "capture_hls",
    "merge_observations",
    "select_hls_url",
]
