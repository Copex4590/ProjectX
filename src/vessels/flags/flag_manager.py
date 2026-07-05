# ============================================================================
# Project X
# Vessel Flag Manager
# ============================================================================

from pathlib import Path

from vessels.flags.flag_record import FlagRecord
from vessels.flags.flag_registry import (
    FlagRegistry,
    flag_registry,
    normalize_country_code,
)


class FlagManager:

    def __init__(self, registry: FlagRegistry | None = None):

        self._registry = registry or flag_registry

    @property
    def flags_dir(self) -> Path:

        return self._registry.flags_dir

    def get_flag(self, country_code: str) -> FlagRecord:

        normalized = normalize_country_code(country_code)

        if normalized is not None:
            record = self._registry.get(normalized)

            if record is not None and self._registry.resolve_svg_path(record) is not None:
                return record

        default_record = self._registry.default_flag()
        default_path = self._registry.resolve_svg_path(default_record)

        if default_path is not None:
            return default_record

        return FlagRecord(
            country_code=normalized or "",
            name="Unknown",
            svg_file="",
            source="builtin",
        )

    def has_flag(self, country_code: str) -> bool:

        return self._registry.has(country_code)

    def register_flag(self, record: FlagRecord) -> FlagRecord:

        return self._registry.register(record)

    def available_flags(self) -> list[str]:

        return self._registry.available_codes()

    def get_flag_file(self, country_code: str) -> Path | None:

        record = self.get_flag(country_code)

        return self._registry.resolve_svg_path(record)


flag_manager = FlagManager()
