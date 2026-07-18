# ============================================================================
# Project X
# Duna Monitor Logbook Format Helpers
# ============================================================================

from __future__ import annotations

from datetime import datetime

from observation.geo_context import geo_context


def sanitize_name(name: str | int | None) -> str:

    if not name:
        return ""

    return str(name).replace("@", "").strip()


def format_timestamp(when: datetime | None = None) -> str:

    current = when or datetime.now()
    return current.strftime("%m.%d - %H:%M")


def calc_distance_km(lat: float, lon: float) -> float:

    distance = geo_context.distance_km(lat, lon)

    if distance is None:
        return 0.0

    return distance


def get_direction(lat: float) -> str:

    coords = geo_context.coordinates()

    if coords is None:
        return ""

    origin_lat, _origin_lon = coords
    return "északra" if lat > origin_lat else "délre"


def get_heading(course: float, speed: float, direction: str) -> str:

    if speed < 0.5:
        return f"Áll {direction}"

    if 90 <= course <= 270:
        return "dél felé halad"

    return "észak felé halad"


def format_distance_cell(distance_km: float, direction: str) -> str:

    return f"{round(distance_km, 2)} km {direction}"


def format_speed_cell(speed: float) -> str:

    if speed < 0.5:
        return ""

    return f"{round(speed, 1)} csomó"


def format_destination_cell(destination: str, eta: str) -> str:

    return f"{sanitize_name(destination)} {sanitize_name(eta)}".strip()


def build_csv_row(ship, *, timestamp: str | None = None) -> str:

    lat = float(getattr(ship, "lat", 0.0) or 0.0)
    lon = float(getattr(ship, "lon", 0.0) or 0.0)
    speed = float(getattr(ship, "speed", 0.0) or 0.0)
    course = float(getattr(ship, "course", 0.0) or 0.0)

    distance_km = getattr(ship, "distance_km", None)

    if distance_km is None:
        distance_km = calc_distance_km(lat, lon)
    else:
        distance_km = float(distance_km)

    direction = getattr(ship, "direction", None) or get_direction(lat)
    heading = getattr(ship, "text_heading", None) or get_heading(
        course,
        speed,
        direction,
    )

    destination = sanitize_name(getattr(ship, "destination", ""))
    eta = sanitize_name(getattr(ship, "eta", ""))
    callsign = sanitize_name(getattr(ship, "callsign", ""))
    draught = getattr(ship, "draft", getattr(ship, "draught", ""))
    mmsi = getattr(ship, "mmsi", "")
    ship_type = sanitize_name(getattr(ship, "ship_type", ""))
    length = getattr(ship, "length", "")
    width = getattr(ship, "width", "")

    current_time = timestamp

    if not current_time:
        last_seen = getattr(ship, "last_seen", None)

        if isinstance(last_seen, datetime):
            current_time = format_timestamp(last_seen)
        else:
            current_time = format_timestamp()

    return (
        f"{current_time};"
        f"{format_distance_cell(distance_km, direction)};"
        f"{heading};"
        f"{format_speed_cell(speed)};"
        f"{format_destination_cell(destination, eta)};"
        f"{callsign};"
        f"{draught};"
        f"{mmsi};"
        f"{ship_type};"
        f"{length};"
        f"{width}\n"
    )
