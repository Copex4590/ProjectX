from engines.timeline.arrival_departure_engine import (
    EVENT_ARRIVAL,
    EVENT_DEPARTURE,
    ArrivalDepartureEngine,
)
from storage.lazy_singleton import lazy_submodule_export

__all__ = [
    "EVENT_ARRIVAL",
    "EVENT_DEPARTURE",
    "ArrivalDepartureEngine",
    "arrival_departure_engine",
]


def __getattr__(name: str):
    if name == "arrival_departure_engine":
        return lazy_submodule_export(__name__, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
