# ============================================================================
# Project X
# Vessel Card Layout Manager
# ============================================================================

from i18n import language_manager
from gui.vesselcard.layouts import (
    CompactLayout,
    DetailedLayout,
    MediaLayout,
    StandardLayout,
)
from preferences import DEFAULT_VESSEL_CARD_LAYOUT, preferences_manager


class VesselCardLayoutManager:

    def __init__(self):

        self._layouts = {
            "compact": CompactLayout(),
            "standard": StandardLayout(),
            "detailed": DetailedLayout(),
            "media": MediaLayout(),
        }

    @property
    def active_layout(self) -> str:

        return preferences_manager.get().vessel_card_layout

    def render(self, ship: dict) -> str:

        layout_name = self.active_layout
        layout = self._layouts.get(layout_name)

        if layout is None:
            layout = self._layouts[DEFAULT_VESSEL_CARD_LAYOUT]

        return layout.render(ship, language_manager.translations())


vessel_card_layout_manager = VesselCardLayoutManager()
