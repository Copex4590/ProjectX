# ============================================================================
# Project X
# Media Vessel Card Layout
# ============================================================================

from gui.vesselcard.layouts.base import (
    build_flag_markup,
    build_photo_section,
    display_value,
    escape_text,
    field_item,
    format_angle,
    format_bool,
    format_speed,
    translate,
    vessel_name,
)


class MediaLayout:

    name = "media"
    css_class = "vessel-card--media"

    def render(self, ship: dict, translations: dict[str, str]) -> str:

        camera_text, camera_class = format_bool(
            translations,
            ship.get("camera_visible"),
        )

        return f"""
            <div class="vessel-card {self.css_class}">
                {build_photo_section(translations, ship)}
                <header class="vessel-card__header">
                    <div class="vessel-card__title-row">
                        {build_flag_markup(ship)}
                        <h2 class="vessel-card__name">{vessel_name(translations, ship)}</h2>
                    </div>
                </header>
                <div class="vessel-card__camera-panel">
                    <div class="vessel-card__camera-title">{escape_text(translate(translations, "Camera Status"))}</div>
                    <div class="vessel-card__camera-value {camera_class}">{escape_text(camera_text)}</div>
                </div>
                <div class="vessel-card__body">
                    <div class="vessel-card__grid">
                        {field_item(translations, "MMSI", escape_text(display_value(ship.get("mmsi"))), mono=True)}
                        {field_item(translations, "Speed", escape_text(format_speed(ship.get("speed"))), mono=True)}
                        {field_item(translations, "Course", escape_text(format_angle(ship.get("course"))), mono=True)}
                        {field_item(translations, "Callsign", escape_text(display_value(ship.get("callsign"))))}
                    </div>
                </div>
            </div>
        """
