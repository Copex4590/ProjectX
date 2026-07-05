# ============================================================================
# Project X
# Vessel Card Layout Helpers
# ============================================================================

from __future__ import annotations

import html
from datetime import datetime
from typing import Any


def escape_text(value: Any) -> str:

    if value is None:
        return ""

    return html.escape(str(value), quote=True)


def translate(translations: dict[str, str], key: str) -> str:

    text = str(key or "").strip()

    if not text:
        return ""

    if text in translations:
        return translations[text]

    return text


def is_empty(value: Any) -> bool:

    if value is None:
        return True

    text = str(value).strip()

    return not text or text in {"None", "null"}


def display_value(value: Any) -> str:

    if is_empty(value):
        return "—"

    return str(value)


def format_coord(value: Any) -> str:

    if is_empty(value):
        return "—"

    try:
        return f"{float(value):.5f}°"
    except (TypeError, ValueError):
        return "—"


def format_number(value: Any, digits: int = 1) -> str:

    if is_empty(value):
        return "—"

    try:
        return f"{float(value):.{digits}f}"
    except (TypeError, ValueError):
        return "—"


def format_angle(value: Any) -> str:

    if is_empty(value):
        return "—"

    try:
        return f"{float(value):.0f}°"
    except (TypeError, ValueError):
        return "—"


def format_speed(value: Any) -> str:

    formatted = format_number(value, 1)

    if formatted == "—":
        return formatted

    return f"{formatted} kn"


def format_distance(value: Any) -> str:

    formatted = format_number(value, 2)

    if formatted == "—":
        return formatted

    return f"{formatted} km"


def format_last_seen(value: Any) -> str:

    if is_empty(value):
        return "—"

    text = str(value).strip()

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return text

    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def format_bool(translations: dict[str, str], value: Any) -> tuple[str, str]:

    if value is True:
        return translate(translations, "Yes"), "vessel-card__value--on"

    if value is False:
        return translate(translations, "No"), "vessel-card__value--off"

    return "—", "vessel-card__value--empty"


def normalize_source(
    translations: dict[str, str],
    value: Any,
) -> tuple[str, str]:

    text = str(value or "").strip().lower()

    if not text:
        return "—", "vessel-card__badge--unknown"

    if "hybrid" in text:
        return translate(translations, "Hybrid"), "vessel-card__badge--hybrid"

    if "rtl" in text:
        return translate(translations, "RTL"), "vessel-card__badge--rtl"

    if "ais" in text:
        return translate(translations, "AIS"), "vessel-card__badge--ais"

    return escape_text(text), "vessel-card__badge--unknown"


def field_item(
    translations: dict[str, str],
    label: str,
    value: str,
    *,
    mono: bool = False,
    full: bool = False,
    state_class: str = "",
) -> str:

    label_text = translate(translations, label)
    classes = [
        "vessel-card__value",
        "vessel-card__value--mono" if mono else "",
        state_class,
        "vessel-card__value--empty" if value == "—" else "",
    ]
    value_class = " ".join(part for part in classes if part)
    item_class = (
        "vessel-card__item vessel-card__item--full"
        if full
        else "vessel-card__item"
    )

    return (
        f'<div class="{item_class}">'
        f'<span class="vessel-card__label">{escape_text(label_text)}</span>'
        f'<span class="{value_class}">{value}</span>'
        f"</div>"
    )


def build_photo_placeholder(translations: dict[str, str]) -> str:

    return f"""
        <div class="vessel-card__photo-placeholder" aria-hidden="true">
            <svg class="vessel-card__photo-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 18h16"></path>
                <path d="M6 18l2-8h8l2 8"></path>
                <path d="M8 10V6h8v4"></path>
                <path d="M12 6V4"></path>
            </svg>
            <span>{escape_text(translate(translations, "No photo available"))}</span>
        </div>
    """


def build_photo_section(translations: dict[str, str], ship: dict) -> str:

    placeholder = build_photo_placeholder(translations)

    if ship.get("has_photo") and ship.get("photo_url"):
        alt_text = (
            translate(translations, "Vessel photo")
            if is_empty(ship.get("name"))
            else escape_text(ship.get("name"))
        )

        return f"""
            <div class="vessel-card__photo">
                <img
                    class="vessel-card__photo-image"
                    src="{escape_text(ship.get('photo_url'))}"
                    alt="{alt_text}"
                    onerror="this.classList.add('vessel-card__photo-image--hidden'); this.parentElement.classList.add('vessel-card__photo--fallback');"
                >
                {placeholder}
            </div>
        """

    return f"""
        <div class="vessel-card__photo vessel-card__photo--placeholder">
            {placeholder}
        </div>
    """


def build_flag_markup(
    ship: dict,
    translations: dict[str, str] | None = None,
) -> str:

    if not ship.get("flag_url"):
        return ""

    flag_code = ship.get("flag_code")
    alt_text = (
        f"{escape_text(flag_code)} {translate(translations or {}, 'flag')}"
        if not is_empty(flag_code)
        else translate(translations or {}, "Default flag")
    )
    fallback = ship.get("flag_fallback_url")
    fallback_attr = (
        f' data-fallback="{escape_text(fallback)}"'
        if fallback
        else ""
    )

    return f"""
        <img
            class="vessel-card__flag"
            src="{escape_text(ship.get('flag_url'))}"
            alt="{alt_text}"{fallback_attr}
            onerror="if (this.dataset.fallback && this.src !== this.dataset.fallback) {{ this.src = this.dataset.fallback; delete this.dataset.fallback; }} else {{ this.classList.add('vessel-card__flag--hidden'); }}"
        >
    """


def vessel_name(translations: dict[str, str], ship: dict) -> str:

    if is_empty(ship.get("name")):
        return escape_text(translate(translations, "Unknown Vessel"))

    return escape_text(ship.get("name"))
