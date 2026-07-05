# ============================================================================
# Project X
# Vessel Card 2.0 — Continuous Information Sheet
# ============================================================================

from __future__ import annotations

from gui.vesselcard.layouts.base import (
    build_flag_markup,
    build_photo_section,
    display_value,
    escape_text,
    format_distance,
    format_last_seen,
    format_number,
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

_LEVEL_SECTIONS = {
    "compact": frozenset({"header", "status", "location"}),
    "standard": frozenset({
        "header",
        "status",
        "location",
        "navigation",
        "identification",
        "camera",
    }),
    "detailed": frozenset({
        "header",
        "status",
        "location",
        "navigation",
        "dimensions",
        "identification",
        "camera",
        "timeline",
        "statistics",
    }),
    "media": frozenset({
        "header",
        "status",
        "location",
        "navigation",
        "dimensions",
        "identification",
        "camera",
        "timeline",
        "statistics",
    }),
}


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


def _status_rows(translations: dict[str, str], ship: dict) -> str:

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
        type_row = f'<div class="vessel-card__type">{type_text}</div>'

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


def _location_rows(translations: dict[str, str], ship: dict) -> str:

    distance_value = ship.get("camera_distance_km")
    if is_empty(distance_value):
        distance_value = ship.get("distance_km")

    return "".join([
        _row(
            translations,
            "Direction",
            _bearing_to_compass(translations, ship.get("camera_bearing_deg")),
        ),
        _row(
            translations,
            "Distance",
            format_distance(distance_value),
        ),
    ])


def _navigation_rows(translations: dict[str, str], ship: dict) -> str:

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


def _dimensions_rows(translations: dict[str, str], ship: dict) -> str:

    return "".join([
        _row(
            translations,
            "Length",
            format_number(ship.get("length"), 1),
        ),
        _row(
            translations,
            "Width",
            format_number(ship.get("width"), 1),
        ),
        _row(
            translations,
            "Draft",
            format_number(ship.get("draft"), 1),
        ),
    ])


def _identification_rows(translations: dict[str, str], ship: dict) -> str:

    return "".join([
        _row(
            translations,
            "MMSI",
            display_value(ship.get("mmsi")),
        ),
        _row(
            translations,
            "IMO",
            display_value(ship.get("imo")),
        ),
        _row(
            translations,
            "Callsign",
            display_value(ship.get("callsign")),
        ),
    ])


def _camera_rows(translations: dict[str, str], ship: dict) -> str:

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
        _row(
            translations,
            "Camera",
            display_value(ship.get("camera_name")),
        ),
        _row(
            translations,
            "Visibility",
            visibility,
            value_class=value_class,
        ),
    ])


def _timeline_rows(translations: dict[str, str], ship: dict) -> str:

    events = ship.get("timeline_events") or []

    if not events:
        return _row(translations, "Latest events", "—")

    lines = []

    for event in events:
        event_type = str(event.get("event_type") or "").strip()
        timestamp = str(event.get("timestamp") or "").strip()
        label = translate(translations, event_type) if event_type else "—"
        lines.append(f"{escape_text(label)} · {escape_text(timestamp)}")

    return _row(
        translations,
        "Latest events",
        "<br>".join(lines),
        allow_html=True,
    )


def _statistics_rows(translations: dict[str, str], ship: dict) -> str:

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


_SECTION_BUILDERS = {
    "header": lambda t, s: _header_section(t, s),
    "status": lambda t, s: _status_rows(t, s),
    "location": lambda t, s: _location_rows(t, s),
    "navigation": lambda t, s: _navigation_rows(t, s),
    "dimensions": lambda t, s: _dimensions_rows(t, s),
    "identification": lambda t, s: _identification_rows(t, s),
    "camera": lambda t, s: _camera_rows(t, s),
    "timeline": lambda t, s: _timeline_rows(t, s),
    "statistics": lambda t, s: _statistics_rows(t, s),
}

_SECTION_ORDER = (
    "header",
    "status",
    "location",
    "navigation",
    "dimensions",
    "identification",
    "camera",
    "timeline",
    "statistics",
)


def render_monitoring_card(
    ship: dict,
    translations: dict[str, str],
    *,
    level: str,
) -> str:

    active_sections = _LEVEL_SECTIONS.get(
        level,
        _LEVEL_SECTIONS["detailed"],
    )
    css_class = f"vessel-card vessel-card--{level} vessel-card--sheet"

    parts: list[str] = []

    for section_name in _SECTION_ORDER:
        if section_name not in active_sections:
            continue

        if parts:
            parts.append(_divider())

        parts.append(_SECTION_BUILDERS[section_name](translations, ship))

    body = "".join(parts)

    return (
        f'<div class="{css_class}">'
        f'<div class="vessel-card__scroll vessel-card__scroll--scrollable">'
        f"{body}"
        f"</div>"
        f"</div>"
    )
