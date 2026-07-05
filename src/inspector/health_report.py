# ============================================================================
# Project X
# Health Report
# ============================================================================

from dataclasses import dataclass
from datetime import datetime

from inspector.component_status import ComponentHealth, ComponentStatus


@dataclass(frozen=True)
class HealthReport:

    overall_status: ComponentStatus
    components: tuple[ComponentHealth, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    generated_at: datetime

    @classmethod
    def from_components(
        cls,
        components: list[ComponentHealth],
        *,
        generated_at: datetime | None = None,
    ) -> "HealthReport":

        timestamp = generated_at or datetime.now()

        warnings = tuple(
            f"{component.name}: {component.message}"
            for component in components
            if component.status == ComponentStatus.WARNING
        )

        errors = tuple(
            f"{component.name}: {component.message}"
            for component in components
            if component.status == ComponentStatus.ERROR
        )

        if components:
            overall_status = max(component.status for component in components)
        else:
            overall_status = ComponentStatus.UNKNOWN

        return cls(
            overall_status=overall_status,
            components=tuple(components),
            warnings=warnings,
            errors=errors,
            generated_at=timestamp,
        )
