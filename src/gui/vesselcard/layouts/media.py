# ============================================================================
# Project X
# Media Vessel Card Layout
# ============================================================================

from gui.vesselcard.layouts.monitoring import render_monitoring_card


class MediaLayout:

    name = "media"
    css_class = "vessel-card--media"

    def render(self, ship: dict, translations: dict[str, str]) -> str:

        return render_monitoring_card(
            ship,
            translations,
            level="media",
        )
