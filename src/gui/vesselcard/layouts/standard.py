# ============================================================================
# Project X
# Standard Vessel Card Layout
# ============================================================================

from gui.vesselcard.layouts.monitoring import render_monitoring_card


class StandardLayout:

    name = "standard"
    css_class = "vessel-card--standard"

    def render(self, ship: dict, translations: dict[str, str]) -> str:

        return render_monitoring_card(
            ship,
            translations,
            level="standard",
        )
