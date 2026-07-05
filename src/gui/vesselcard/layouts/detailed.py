# ============================================================================
# Project X
# Detailed Vessel Card Layout
# ============================================================================

from gui.vesselcard.layouts.monitoring import render_monitoring_card


class DetailedLayout:

    name = "detailed"
    css_class = "vessel-card--detailed"

    def render(self, ship: dict, translations: dict[str, str]) -> str:

        return render_monitoring_card(
            ship,
            translations,
            level="detailed",
        )
