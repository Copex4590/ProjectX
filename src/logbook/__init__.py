# ============================================================================
# Project X
# Logbook Package
# ============================================================================

from logbook.logbook_manager import LegacyImportResult, LogbookManager
from logbook.logbook_recorder import LogbookRecorder
from logbook.paths import logbook_dir
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "LegacyImportResult",
    "LogbookManager",
    "LogbookRecorder",
    "logbook_dir",
    "logbook_manager",
    "logbook_recorder",
]


def __getattr__(name: str):
    if name == "logbook_manager":
        return lazy_submodule_export(__name__, name)
    if name == "logbook_recorder":
        return lazy_submodule_export(__name__, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
