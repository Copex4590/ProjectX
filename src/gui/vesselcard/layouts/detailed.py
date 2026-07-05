# ============================================================================
# Project X
# Detailed Vessel Card Layout
# ============================================================================

from gui.vesselcard.layouts.base import (
    build_flag_markup,
    build_photo_section,
    display_value,
    escape_text,
    field_item,
    format_angle,
    format_bool,
    format_coord,
    format_distance,
    format_last_seen,
    format_number,
    format_speed,
    is_empty,
    normalize_source,
    translate,
    vessel_name,
)


class DetailedLayout:

    name = "detailed"
    css_class = "vessel-card--detailed"

    def render(self, ship: dict, translations: dict[str, str]) -> str:

        type_label = escape_text(display_value(ship.get("ship_type")))
        source_label, source_class = normalize_source(ship.get("source"))
        ais_text, ais_class = format_bool(translations, ship.get("ais_visible"))
        rtl_text, rtl_class = format_bool(translations, ship.get("rtl_visible"))
        camera_text, camera_class = format_bool(
            translations,
            ship.get("camera_visible"),
        )

        icon_id = (
            '<svg class="vessel-card__block-icon" viewBox="0 0 24 24" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<rect x="3" y="4" width="18" height="16" rx="2"/>'
            '<path d="M7 8h4"/><path d="M7 12h10"/><path d="M7 16h6"/></svg>'
        )
        icon_pos = (
            '<svg class="vessel-card__block-icon" viewBox="0 0 24 24" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M12 21s7-4.5 7-11a7 7 0 1 0-14 0c0 6.5 7 11 7 11z"/>'
            '<circle cx="12" cy="10" r="2.5"/></svg>'
        )
        icon_nav = (
            '<svg class="vessel-card__block-icon" viewBox="0 0 24 24" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<circle cx="12" cy="12" r="9"/><path d="M12 3v3"/><path d="M12 18v3"/>'
            '<path d="M3 12h3"/><path d="M18 12h3"/>'
            '<path d="m14.5 9.5-5 2 2 5 5-2-2-5z"/></svg>'
        )
        icon_voy = (
            '<svg class="vessel-card__block-icon" viewBox="0 0 24 24" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M4 18h16"/><path d="M6 18l2-8h8l2 8"/>'
            '<path d="M8 10V6h8v4"/><path d="M12 6V4"/></svg>'
        )
        icon_vis = (
            '<svg class="vessel-card__block-icon" viewBox="0 0 24 24" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z"/>'
            '<circle cx="12" cy="12" r="3"/></svg>'
        )
        icon_meta = (
            '<svg class="vessel-card__block-icon" viewBox="0 0 24 24" fill="none" '
            'stroke-width="2" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M4 6h16"/><path d="M4 12h10"/><path d="M4 18h14"/></svg>'
        )

        badges = []

        if not is_empty(ship.get("ship_type")):
            badges.append(
                '<span class="vessel-card__badge vessel-card__badge--type">'
                f'<span class="vessel-card__badge-dot"></span>{type_label}</span>'
            )

        if source_label != "—":
            badges.append(
                f'<span class="vessel-card__badge vessel-card__badge--source {source_class}">'
                f'<span class="vessel-card__badge-dot"></span>{escape_text(source_label)}</span>'
            )

        timeline_summary = escape_text(display_value(ship.get("timeline_summary")))
        statistics_summary = escape_text(display_value(ship.get("statistics_summary")))

        return f"""
            <div class="vessel-card {self.css_class}">
                <header class="vessel-card__header">
                    <div class="vessel-card__title-row">
                        {build_flag_markup(ship)}
                        <h2 class="vessel-card__name">{vessel_name(translations, ship)}</h2>
                    </div>
                    <div class="vessel-card__badges">{"".join(badges)}</div>
                </header>
                {build_photo_section(translations, ship)}
                <div class="vessel-card__body">
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_id}{escape_text(translate(translations, "Identification"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "MMSI", escape_text(display_value(ship.get("mmsi"))), mono=True)}
                            {field_item(translations, "IMO", escape_text(display_value(ship.get("imo"))), mono=True)}
                            {field_item(translations, "Callsign", escape_text(display_value(ship.get("callsign"))))}
                            {field_item(translations, "Type", escape_text(display_value(ship.get("ship_type"))))}
                            {field_item(translations, "Source", escape_text(display_value(ship.get("source"))))}
                        </div>
                    </section>
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_pos}{escape_text(translate(translations, "Position"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "Latitude", escape_text(format_coord(ship.get("lat"))), mono=True)}
                            {field_item(translations, "Longitude", escape_text(format_coord(ship.get("lon"))), mono=True)}
                            {field_item(translations, "Distance", escape_text(format_distance(ship.get("distance_km"))), mono=True)}
                            {field_item(translations, "Direction", escape_text(display_value(ship.get("direction"))))}
                        </div>
                    </section>
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_nav}{escape_text(translate(translations, "Navigation"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "Speed", escape_text(format_speed(ship.get("speed"))), mono=True)}
                            {field_item(translations, "Course", escape_text(format_angle(ship.get("course"))), mono=True)}
                            {field_item(translations, "Heading", escape_text(format_angle(ship.get("heading"))), mono=True)}
                            {field_item(translations, "Text Heading", escape_text(display_value(ship.get("text_heading"))))}
                        </div>
                    </section>
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_voy}{escape_text(translate(translations, "Voyage"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "Destination", escape_text(display_value(ship.get("destination"))), full=True)}
                            {field_item(translations, "ETA", escape_text(display_value(ship.get("eta"))))}
                            {field_item(translations, "Last Seen", escape_text(format_last_seen(ship.get("last_seen"))))}
                        </div>
                    </section>
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_meta}{escape_text(translate(translations, "Dimensions"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "Length", escape_text(format_number(ship.get("length"), 1)), mono=True)}
                            {field_item(translations, "Width", escape_text(format_number(ship.get("width"), 1)), mono=True)}
                            {field_item(translations, "Draft", escape_text(format_number(ship.get("draft"), 1)), mono=True)}
                        </div>
                    </section>
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_vis}{escape_text(translate(translations, "Visibility"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "AIS Visible", escape_text(ais_text), state_class=ais_class)}
                            {field_item(translations, "RTL Visible", escape_text(rtl_text), state_class=rtl_class)}
                            {field_item(translations, "Camera Visible", escape_text(camera_text), state_class=camera_class)}
                        </div>
                    </section>
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_meta}{escape_text(translate(translations, "Timeline Summary"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "Timeline Summary", timeline_summary, full=True)}
                        </div>
                    </section>
                    <section class="vessel-card__block">
                        <h3 class="vessel-card__block-title">{icon_meta}{escape_text(translate(translations, "Statistics Summary"))}</h3>
                        <div class="vessel-card__grid">
                            {field_item(translations, "Statistics Summary", statistics_summary, full=True)}
                        </div>
                    </section>
                </div>
            </div>
        """
