# ============================================================================
# Project X
# RTL-SDR Provider Window
# ============================================================================

from __future__ import annotations

from gui.providers.provider_window import ProviderWindow


class RTLWindow(ProviderWindow):
    def provider_icon(self) -> str:

        return "📻"

    def provider_title_key(self) -> str:

        return "RTL-SDR"

    def _sections(self) -> list[tuple[str, list[tuple[str, str]]]]:

        return [
            (
                "Provider information",
                [
                    ("Provider", "RTL-SDR"),
                    ("Type", "Local receiver"),
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
