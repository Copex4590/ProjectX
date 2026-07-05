# ============================================================================
# Project X
# Monitoring Vessel Card Layout
# ============================================================================

from __future__ import annotations

from gui.vesselcard.layouts.base import (
    build_flag_markup,
    build_photo_section,
    display_value,
    escape_text,
    format_distance,
    format_last_seen,
    is_empty,
    translate,
    vessel_name,
)

_COMPASS_KEYS = (
    "North",
    "Northeast",
    "East",
    "Southeast",
    "South",
    "Southwest",
    "West",
    "Northwest",
)

_UNDERWAY_THRESHOLD_KN = 0.5
_KN_TO_KMH = 1.852


def _row(
    translations: dict[str, str],
    label: str,
    value: str,
    *,
    value_class: str = "",
    allow_html: bool = False,
) -> str:

    label_text = escape_text(translate(translations, label))
    value_text = value if allow_html else escape_text(value)
    classes = " ".join(
        part
        for part in ("vessel-card__value", value_class)
        if part
    )

    return (
        f'<div class="vessel-card__row">'
        f'<span class="vessel-card__label">{label_text}</span>'
        f'<span class="{classes}">{value_text}</span>'
        f"</div>"
    )


def _divider() -> str:

    return '<div class="vessel-card__divider"></div>'


def _bearing_to_compass(
    translations: dict[str, str],
    bearing_deg,
) -> str:

    if is_empty(bearing_deg):
        return "—"

    try:
        bearing = float(bearing_deg) % 360.0
    except (TypeError, ValueError):
        return "—"

    index = int((bearing + 22.5) / 45.0) % 8
    return translate(translations, _COMPASS_KEYS[index])


def _speed_knots(speed) -> float:

    if is_empty(speed):
        return 0.0

    try:
        return float(speed)
    except (TypeError, ValueError):
        return 0.0


def _status_row(translations: dict[str, str], ship: dict) -> str:

    speed_kn = _speed_knots(ship.get("speed"))

    if speed_kn < _UNDERWAY_THRESHOLD_KN:
        value = f"⚓ {escape_text(translate(translations, 'MOORED'))}"
        return _row(translations, "Status", value, allow_html=True)

    kmh = speed_kn * _KN_TO_KMH
    underway = escape_text(translate(translations, "UNDERWAY"))
    value = (
        f"🚢 {underway}<br>"
        f"{kmh:.1f} km/h ({speed_kn:.1f} kn)"
    )
    return _row(translations, "Status", value, allow_html=True)


def _header_section(translations: dict[str, str], ship: dict) -> str:

    type_text = escape_text(display_value(ship.get("ship_type")))
    type_row = ""

    if type_text != "—":
        type_row = (
            f'<div class="vessel-card__type">'
            f'{type_text}'
            f"</div>"
        )

    return (
        f'<div class="vessel-card__hero">'
        f'{build_photo_section(translations, ship)}'
        f'<div class="vessel-card__identity">'
        f'<div class="vessel-card__title-row">'
        f'{build_flag_markup(ship, translations)}'
        f'<h2 class="vessel-card__name">{vessel_name(translations, ship)}</h2>'
        f"</div>"
        f"{type_row}"
        f"</div>"
        f"</div>"
    )


def _location_section(translations: dict[str, str], ship: dict) -> str:

    distance_value = ship.get("camera_distance_km")
    if is_empty(distance_value):
        distance_value = ship.get("distance_km")

    direction = _bearing_to_compass(
        translations,
        ship.get("camera_bearing_deg"),
    )

    rows = [
        _row(translations, "Direction", direction),
        _row(
            translations,
            "Distance",
            format_distance(distance_value),
        ),
    ]

    return "".join(rows)


def _navigation_section(translations: dict[str, str], ship: dict) -> str:

    return "".join([
        _row(
            translations,
            "Destination",
            display_value(ship.get("destination")),
        ),
        _row(
            translations,
            "ETA",
            display_value(ship.get("eta")),
        ),
    ])


def _camera_section(translations: dict[str, str], ship: dict) -> str:

    camera_name = display_value(ship.get("camera_name"))

    if ship.get("camera_visible") is True:
        visibility = translate(translations, "Visible")
        value_class = "vessel-card__value--on"
    elif ship.get("camera_visible") is False:
        visibility = translate(translations, "Not visible")
        value_class = "vessel-card__value--off"
    else:
        visibility = "—"
        value_class = "vessel-card__value--empty"

    return "".join([
        _row(translations, "Camera", camera_name),
        _row(
            translations,
            "Camera Visible",
            visibility,
            value_class=value_class,
        ),
    ])


def _timeline_section(translations: dict[str, str], ship: dict) -> str:

    events = ship.get("timeline_events") or []

    if not events:
        return _row(
            translations,
            "Latest events",
            "—",
        )

    lines = []

    for event in events:
        event_type = str(event.get("event_type") or "").strip()
        timestamp = str(event.get("timestamp") or "").strip()
        label = translate(translations, event_type) if event_type else "—"
        lines.append(f"{escape_text(label)} · {escape_text(timestamp)}")

    value = "<br>".join(lines)
    return _row(
        translations,
        "Latest events",
        value,
        allow_html=True,
    )


def _statistics_section(translations: dict[str, str], ship: dict) -> str:

    return "".join([
        _row(
            translations,
            "First seen",
            format_last_seen(ship.get("stats_first_seen")),
        ),
        _row(
            translations,
            "Last seen",
            format_last_seen(ship.get("stats_last_seen")),
        ),
        _row(
            translations,
            "Observation count",
            display_value(ship.get("stats_observation_count")),
        ),
    ])


def _compact_extras(translations: dict[str, str], ship: dict) -> str:

    return _row(
        translations,
        "MMSI",
        display_value(ship.get("mmsi")),
    )


def render_monitoring_card(
    ship: dict,
    translations: dict[str, str],
    *,
    level: str,
) -> str:

    css_class = f"vessel-card--{level}"
    scroll_class = "vessel-card__scroll"

    if level == "detailed":
        scroll_class += " vessel-card__scroll--scrollable"

    sections: list[str] = [_header_section(translations, ship), _divider()]
    sections.append(_status_row(translations, ship))
    sections.append(_divider())
    sections.append(_location_section(translations, ship))

    if level == "compact":
        sections.append(_divider())
        sections.append(_compact_extras(translations, ship))
    else:
        sections.append(_divider())
        sections.append(_navigation_section(translations, ship))

        if level == "media":
            sections.append(_divider())
            sections.append(_camera_section(translations, ship))
        elif level in {"standard", "detailed"}:
            sections.append(_divider())
            sections.append(_camera_section(translations, ship))

        if level == "detailed":
            sections.append(_divider())
            sections.append(_timeline_section(translations, ship))
            sections.append(_divider())
            sections.append(_statistics_section(translations, ship))

    body = "".join(sections)

    return (
        f'<div class="vessel-card {css_class}">'
        f'<div class="{scroll_class}">{body}</div>'
        f"</div>"
    )
