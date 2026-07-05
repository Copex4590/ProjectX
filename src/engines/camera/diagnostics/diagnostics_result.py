# ============================================================================
# Project X
# Camera Diagnostics Result
# ============================================================================

from dataclasses import dataclass
from enum import Enum


class DiagnosticSeverity(Enum):

    OK = "ok"
    WARNING = "warning"
    ERROR = "error"

    def __lt__(self, other: "DiagnosticSeverity") -> bool:

        order = {
            DiagnosticSeverity.OK: 0,
            DiagnosticSeverity.WARNING: 1,
            DiagnosticSeverity.ERROR: 2,
        }
        return order[self] < order[other]


@dataclass(frozen=True)
class DiagnosticResult:

    camera_id: str
    severity: DiagnosticSeverity
    message: str
    recommendation: str
    category: str = "general"


@dataclass(frozen=True)
class CameraDiagnosticsReport:

    camera_id: str
    results: tuple[DiagnosticResult, ...]

    @property
    def status(self) -> DiagnosticSeverity:

        if not self.results:
            return DiagnosticSeverity.OK

        return max(result.severity for result in self.results)

    @property
    def ok(self) -> bool:

        return self.status == DiagnosticSeverity.OK

    @property
    def errors(self) -> tuple[DiagnosticResult, ...]:

        return tuple(
            result
            for result in self.results
            if result.severity == DiagnosticSeverity.ERROR
        )

    @property
    def warnings(self) -> tuple[DiagnosticResult, ...]:

        return tuple(
            result
            for result in self.results
            if result.severity == DiagnosticSeverity.WARNING
        )
