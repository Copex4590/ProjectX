# ============================================================================
# Project X — Camera engines package
# ============================================================================

from .camera_match import CameraMatch, build_camera_match
from .camera_selection_engine import CameraSelectionEngine, camera_selection_engine
from .coverage_model import CameraCoverageModel, CoverageSector, camera_coverage_model
from .link_manager import (
    CameraLinkSnapshot,
    IntelligentCameraLinkManager,
    intelligent_camera_link_manager,
)
from .link_states import (
    EVENT_CAMERA_COVERAGE_TOGGLED,
    EVENT_CAMERA_LINK_CHANGED,
    EVENT_CAMERA_LINK_MODE,
    CameraLinkMode,
    CameraLinkState,
)
from .scoring_engine import (
    CameraScoringEngine,
    ScoreBreakdown,
    ScoredCamera,
    camera_scoring_engine,
)

# Eager binds so `from engines.camera import camera_selection_engine` is the
# singleton, not the submodule module object.

__all__ = [
    "CameraMatch",
    "build_camera_match",
    "CameraSelectionEngine",
    "camera_selection_engine",
    "CameraScoringEngine",
    "camera_scoring_engine",
    "ScoredCamera",
    "ScoreBreakdown",
    "CameraCoverageModel",
    "camera_coverage_model",
    "CoverageSector",
    "IntelligentCameraLinkManager",
    "intelligent_camera_link_manager",
    "CameraLinkSnapshot",
    "CameraLinkState",
    "CameraLinkMode",
    "EVENT_CAMERA_LINK_CHANGED",
    "EVENT_CAMERA_LINK_MODE",
    "EVENT_CAMERA_COVERAGE_TOGGLED",
    "CameraDiagnosticsEngine",
    "CameraDiagnosticsReport",
    "DiagnosticResult",
    "DiagnosticSeverity",
    "camera_diagnostics_engine",
    "CameraProvider",
    "ProviderRegistry",
    "ProviderSession",
    "ProviderState",
    "ProviderStatus",
    "provider_registry",
    "register_default_providers",
]

_LAZY_EXPORTS = {
    "CameraDiagnosticsEngine": (".diagnostics", "CameraDiagnosticsEngine"),
    "CameraDiagnosticsReport": (".diagnostics", "CameraDiagnosticsReport"),
    "DiagnosticResult": (".diagnostics", "DiagnosticResult"),
    "DiagnosticSeverity": (".diagnostics", "DiagnosticSeverity"),
    "camera_diagnostics_engine": (".diagnostics", "camera_diagnostics_engine"),
    "CameraProvider": (".providers", "CameraProvider"),
    "ProviderRegistry": (".providers", "ProviderRegistry"),
    "ProviderSession": (".providers", "ProviderSession"),
    "ProviderState": (".providers", "ProviderState"),
    "ProviderStatus": (".providers", "ProviderStatus"),
    "provider_registry": (".providers", "provider_registry"),
    "register_default_providers": (".providers", "register_default_providers"),
}


def __getattr__(name: str):

    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _LAZY_EXPORTS[name]
    module = __import__(f"{__name__}{module_name}", fromlist=[attribute_name])
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
