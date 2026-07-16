# ============================================================================
# Project X
# AISStream Provider Window
# ============================================================================

from __future__ import annotations

from gui.providers.provider_window import ProviderWindow


class AISStreamWindow(ProviderWindow):
    def provider_icon(self) -> str:

        return "📡"

    def provider_title_key(self) -> str:

        return "AISStream"

    def _sections(self) -> list[tuple[str, list[tuple[str, str]]]]:

        return [
            (
                "Provider information",
                [
                    ("Provider", "AISStream"),
                    ("Type", "Internet AIS"),
                ],
            ),
            (
                "Connection status",
                [
                    ("Status", "Not available"),
                ],
            ),
            (
                "Configuration",
                [
                    ("Status", "Not configured"),
                ],
            ),
        ]
