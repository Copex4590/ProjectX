# ============================================================================
# Project X
# Component Status
# ============================================================================

from dataclasses import dataclass
from enum import Enum


class ComponentStatus(Enum):

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    UNKNOWN = "unknown"

    def __lt__(self, other: "ComponentStatus") -> bool:

        order = {
            ComponentStatus.OK: 0,
            ComponentStatus.UNKNOWN: 1,
            ComponentStatus.WARNING: 2,
            ComponentStatus.ERROR: 3,
        }
        return order[self] < order[other]


@dataclass(frozen=True)
class ComponentHealth:

    name: str
    status: ComponentStatus
    message: str
    version: str = ""
