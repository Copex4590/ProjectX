# ============================================================================
# Project X
# Compact Vessel Card Layout
# ============================================================================

from gui.vesselcard.layouts.monitoring import render_monitoring_card


class CompactLayout:

    name = "compact"
    css_class = "vessel-card--compact"

    def render(self, ship: dict, translations: dict[str, str]) -> str:

        return render_monitoring_card(
            ship,
            translations,
            level="compact",
        )
