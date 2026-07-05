# ============================================================================
# Project X
# Compact Vessel Card Layout
# ============================================================================

from gui.vesselcard.layouts.base import (
    build_flag_markup,
    build_photo_section,
    display_value,
    escape_text,
    field_item,
    format_angle,
    format_bool,
    format_last_seen,
    format_speed,
    vessel_name,
)


class CompactLayout:

    name = "compact"
    css_class = "vessel-card--compact"

    def render(self, ship: dict, translations: dict[str, str]) -> str:

        camera_text, camera_class = format_bool(
            translations,
            ship.get("camera_visible"),
        )

        fields = [
            field_item(
                translations,
                "MMSI",
                escape_text(display_value(ship.get("mmsi"))),
                mono=True,
            ),
            field_item(
                translations,
                "Type",
                escape_text(display_value(ship.get("ship_type"))),
            ),
            field_item(
                translations,
                "Speed",
                escape_text(format_speed(ship.get("speed"))),
                mono=True,
            ),
            field_item(
                translations,
                "Course",
                escape_text(format_angle(ship.get("course"))),
                mono=True,
            ),
            field_item(
                translations,
                "Last Seen",
                escape_text(format_last_seen(ship.get("last_seen"))),
            ),
            field_item(
                translations,
                "Camera Status",
                escape_text(camera_text),
                state_class=camera_class,
            ),
        ]

        return f"""
            <div class="vessel-card {self.css_class}">
                {build_photo_section(translations, ship)}
                <header class="vessel-card__header">
                    <div class="vessel-card__title-row">
                        {build_flag_markup(ship)}
                        <h2 class="vessel-card__name">{vessel_name(translations, ship)}</h2>
                    </div>
                </header>
                <div class="vessel-card__body">
                    <div class="vessel-card__grid">
                        {"".join(fields)}
                    </div>
                </div>
            </div>
        """
