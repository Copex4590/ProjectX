# ============================================================================
# Project X
# Vessel Flag Record
# ============================================================================

from dataclasses import dataclass


@dataclass
class FlagRecord:

    country_code: str
    name: str = ""
    svg_file: str = ""
    source: str = "builtin"

    def normalized_country_code(self) -> str:

        return str(self.country_code).strip().upper()

    def safe_text(self, value: str | None) -> str:

        if value is None:
            return ""

        return str(value).strip()
