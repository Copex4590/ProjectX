from .statistics_manager import StatisticsManager
from .statistics_record import (
    ActiveVesselEntry,
    DashboardStatistics,
    GlobalStatistics,
    VesselStatistics,
)
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "ActiveVesselEntry",
    "DashboardStatistics",
    "GlobalStatistics",
    "StatisticsManager",
    "VesselStatistics",
    "statistics_manager",
]


def __getattr__(name: str):
    if name == "statistics_manager":
        return lazy_submodule_export(__name__, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
