from .camera_match import CameraMatch, build_camera_match

__all__ = [
    "CameraMatch",
    "build_camera_match",
    "CameraSelectionEngine",
    "camera_selection_engine",
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
    "CameraSelectionEngine": (".camera_selection_engine", "CameraSelectionEngine"),
    "camera_selection_engine": (".camera_selection_engine", "camera_selection_engine"),
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
