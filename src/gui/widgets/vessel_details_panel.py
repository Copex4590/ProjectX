# ============================================================================
# Project X
# Vessel Details Panel 2.0 (SAVE-213)
# ============================================================================

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from database import registry
from database.vessel_database import vessel_database
from database.vessel_database_manager import (
    EVENT_SYNC_COMPLETED,
    vessel_database_manager,
)
from engines.camera import camera_selection_engine
from events import eventbus
from gui.i18n_support import bind_language_refresh
from gui.theme import ThemeColors, card_stylesheet
from gui.vesselcard.layouts.base import (
    display_value,
    format_angle,
    format_coord,
    format_distance,
    format_last_seen,
    format_number,
    format_speed,
    is_empty,
)
from i18n import tr
from models.ship import Ship
from vessels.flags.flag_manager import flag_manager
from vessels.photo_manager import photo_manager

logger = logging.getLogger(__name__)

_ONLINE_THRESHOLD_S = 60.0
_STALE_THRESHOLD_S = 300.0


class _GuiBridge(QObject):
    """Marshal EventBus callbacks onto the Qt GUI thread."""

    refresh_requested = Signal()


def _dash(value) -> str:

    return display_value(value)


def _coalesce(*values) -> str:

    for value in values:
        if not is_empty(value):
            return str(value).strip()
    return ""


def _format_signal_age(last_seen: datetime | None) -> tuple[str, str, str]:
    """Return (age_text, status_text, status_color)."""

    if last_seen is None:
        return "—", "Offline", ThemeColors.Danger

    if last_seen.tzinfo is not None:
        now = datetime.now(timezone.utc)
        seen = last_seen.astimezone(timezone.utc)
    else:
        now = datetime.now()
        seen = last_seen

    age_s = max(0.0, (now - seen).total_seconds())

    if age_s < 60:
        age_text = f"{int(age_s)}s"
    elif age_s < 3600:
        age_text = f"{int(age_s // 60)}m"
    elif age_s < 86400:
        age_text = f"{age_s / 3600:.1f}h"
    else:
        age_text = f"{age_s / 86400:.1f}d"

    if age_s <= _ONLINE_THRESHOLD_S:
        return age_text, "Online", ThemeColors.Success
    if age_s <= _STALE_THRESHOLD_S:
        return age_text, "Stale", ThemeColors.Warning
    return age_text, "Offline", ThemeColors.Danger


def _provider_label(ship: Ship | None) -> str:

    if ship is None:
        return ""

    source = str(ship.source or "").strip()
    if source:
        return source

    if ship.ais_visible and ship.rtl_visible:
        return "Hybrid"
    if ship.rtl_visible:
        return "RTL-SDR"
    if ship.ais_visible:
        return "AISStream"
    return ""


class _SectionCard(QFrame):

    def __init__(self, title_key: str, parent=None):
        super().__init__(parent)

        self._title_key = title_key
        self.setStyleSheet(card_stylesheet(radius=10))

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 11pt; font-weight: 700;"
        )
        root.addWidget(self._title)

        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet(f"background: {ThemeColors.Border};")
        root.addWidget(divider)

        self.grid = QGridLayout()
        self.grid.setContentsMargins(0, 2, 0, 0)
        self.grid.setHorizontalSpacing(10)
        self.grid.setVerticalSpacing(6)
        root.addLayout(self.grid)

        self.body = QVBoxLayout()
        self.body.setContentsMargins(0, 4, 0, 0)
        self.body.setSpacing(8)
        root.addLayout(self.body)

        self._rows: list[tuple[QLabel, QLabel, str]] = []

    def add_field(self, label_key: str) -> QLabel:

        row = len(self._rows)
        caption = QLabel()
        caption.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt;"
        )
        value = QLabel("—")
        value.setWordWrap(True)
        value.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        value.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 10pt; font-weight: 600;"
        )
        self.grid.addWidget(caption, row, 0, Qt.AlignmentFlag.AlignTop)
        self.grid.addWidget(value, row, 1, Qt.AlignmentFlag.AlignTop)
        self.grid.setColumnStretch(1, 1)
        self._rows.append((caption, value, label_key))
        return value

    def set_value(self, value_label: QLabel, text: str, *, color: str | None = None) -> None:

        value_label.setText(text if text else "—")
        resolved = color or ThemeColors.TextPrimary
        if text in ("", "—"):
            resolved = ThemeColors.TextSecondary
        value_label.setStyleSheet(
            f"color: {resolved}; font-size: 10pt; font-weight: 600;"
        )

    def refresh_translations(self) -> None:

        self._title.setText(tr(self._title_key))
        for caption, _value, key in self._rows:
            caption.setText(tr(key))


class _PlaceholderBox(QFrame):

    def __init__(self, icon: str, message_key: str, parent=None):
        super().__init__(parent)

        self._message_key = message_key
        self.setMinimumHeight(120)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setStyleSheet(
            f"""
            QFrame {{
                background: {ThemeColors.panel_elevated()};
                border: 1px dashed {ThemeColors.Border};
                border-radius: 8px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(6)

        self._icon = QLabel(icon)
        self._icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._icon.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 28pt; border: none;"
        )
        layout.addWidget(self._icon)

        self._message = QLabel()
        self._message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._message.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 9pt; border: none;"
        )
        layout.addWidget(self._message)

        self._image = QLabel()
        self._image.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image.setVisible(False)
        self._image.setStyleSheet("border: none;")
        layout.addWidget(self._image)

    def refresh_translations(self) -> None:

        self._message.setText(tr(self._message_key))

    def show_placeholder(self) -> None:

        self._image.clear()
        self._image.setVisible(False)
        self._icon.setVisible(True)
        self._message.setVisible(True)

    def show_image(self, path: Path | None) -> None:

        if path is None or not path.is_file():
            self.show_placeholder()
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.show_placeholder()
            return

        scaled = pixmap.scaled(
            280,
            140,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._image.setPixmap(scaled)
        self._image.setVisible(True)
        self._icon.setVisible(False)
        self._message.setVisible(False)


class VesselDetailsPanel(QWidget):
    """Modern vessel data sheet updated from ShipRegistry selection."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._mmsi: int | None = None
        self._sections: list[_SectionCard] = []
        self._bus = _GuiBridge(self)
        self._bus.refresh_requested.connect(self.refresh)

        self.setMinimumWidth(320)
        self.setMaximumWidth(420)
        self.setStyleSheet(f"background: {ThemeColors.Background};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            f"QScrollArea {{ background: {ThemeColors.Background}; border: none; }}"
        )
        outer.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet(f"background: {ThemeColors.Background};")
        scroll.setWidget(content)

        layout = QVBoxLayout(content)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        header = QHBoxLayout()
        self._title = QLabel()
        self._title.setStyleSheet(
            f"color: {ThemeColors.TextPrimary}; font-size: 14pt; font-weight: 700;"
        )
        header.addWidget(self._title)
        header.addStretch(1)
        self._status_badge = QLabel("—")
        self._status_badge.setStyleSheet(self._badge_style(ThemeColors.TextSecondary))
        header.addWidget(self._status_badge)
        layout.addLayout(header)

        self._empty_label = QLabel()
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setStyleSheet(
            f"color: {ThemeColors.TextSecondary}; font-size: 10pt; padding: 24px;"
        )
        layout.addWidget(self._empty_label)

        self._overview = self._add_section(layout, "Overview")
        self._name = self._overview.add_field("Name")
        self._mmsi_value = self._overview.add_field("MMSI")
        self._imo = self._overview.add_field("IMO")
        self._callsign = self._overview.add_field("Callsign")
        self._flag = self._overview.add_field("Flag")
        self._ship_type = self._overview.add_field("Ship Type")
        self._flag_image = QLabel()
        self._flag_image.setFixedHeight(28)
        self._flag_image.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self._overview.body.addWidget(self._flag_image)
        self._photo_box = _PlaceholderBox("🛳", "No photo available")
        self._overview.body.addWidget(self._photo_box)

        self._position = self._add_section(layout, "Position")
        self._lat = self._position.add_field("Latitude")
        self._lon = self._position.add_field("Longitude")
        self._speed = self._position.add_field("Speed")
        self._course = self._position.add_field("Course")
        self._heading = self._position.add_field("Heading")
        self._rot = self._position.add_field("ROT")
        self._nav_status = self._position.add_field("Navigational Status")

        self._voyage = self._add_section(layout, "Voyage")
        self._departure = self._voyage.add_field("Departure Port")
        self._destination = self._voyage.add_field("Destination")
        self._eta = self._voyage.add_field("ETA")
        self._draught = self._voyage.add_field("Draught")
        self._cargo = self._voyage.add_field("Cargo")

        self._vessel = self._add_section(layout, "Vessel")
        self._length = self._vessel.add_field("Length")
        self._width = self._vessel.add_field("Width")
        self._year_built = self._vessel.add_field("Year Built")
        self._gt = self._vessel.add_field("GT")
        self._dwt = self._vessel.add_field("DWT")

        self._live = self._add_section(layout, "Live Status")
        self._ais_provider = self._live.add_field("AIS Provider")
        self._last_update = self._live.add_field("Last Update")
        self._signal_age = self._live.add_field("Signal Age")
        self._online = self._live.add_field("Status")

        self._camera = self._add_section(layout, "Camera")
        self._camera_name = self._camera.add_field("Nearest Camera")
        self._camera_distance = self._camera.add_field("Camera Distance")
        self._camera_box = _PlaceholderBox("📷", "Camera preview placeholder")
        self._camera.body.addWidget(self._camera_box)

        self._database = self._add_section(layout, "Database")
        self._db_status = self._database.add_field("Local Database")
        self._db_last_sync = self._database.add_field("Last Sync")
        self._db_record_id = self._database.add_field("Record ID")

        layout.addStretch(1)

        bind_language_refresh(self.refresh_translations)
        self.refresh_translations()
        self.clear()
        self._connect_eventbus()

    def _connect_eventbus(self) -> None:

        eventbus.subscribe("ship.updated", self._on_ship_updated_event)
        eventbus.subscribe(EVENT_SYNC_COMPLETED, self._on_sync_event)

    def _on_ship_updated_event(self, *args, **kwargs) -> None:

        if self._mmsi is None:
            return
        self._bus.refresh_requested.emit()

    def _on_sync_event(self, *args, **kwargs) -> None:

        if self._mmsi is None:
            return
        self._bus.refresh_requested.emit()

    def _badge_style(self, color: str) -> str:

        return (
            f"color: {ThemeColors.TextPrimary}; background: {color}; "
            f"border-radius: 10px; padding: 3px 10px; font-size: 9pt; font-weight: 700;"
        )

    def _add_section(self, layout: QVBoxLayout, title_key: str) -> _SectionCard:

        card = _SectionCard(title_key)
        self._sections.append(card)
        layout.addWidget(card)
        return card

    def refresh_translations(self) -> None:

        self._title.setText(tr("Vessel Details"))
        self._empty_label.setText(tr("Select a vessel to view details."))
        for section in self._sections:
            section.refresh_translations()
        self._photo_box.refresh_translations()
        self._camera_box.refresh_translations()
        self.refresh()

    def clear(self) -> None:

        self._mmsi = None
        self._empty_label.setVisible(True)
        for section in self._sections:
            section.setVisible(False)
        self._status_badge.setText("—")
        self._status_badge.setStyleSheet(self._badge_style(ThemeColors.TextSecondary))
        self._flag_image.clear()
        self._photo_box.show_placeholder()
        self._camera_box.show_placeholder()

    def set_mmsi(self, mmsi: int | None) -> None:

        if mmsi is None:
            self.clear()
            return

        try:
            self._mmsi = int(mmsi)
        except (TypeError, ValueError):
            self.clear()
            return

        self.refresh()

    def bind_ship(self, ship: Ship | None) -> None:

        if ship is None:
            self.clear()
            return
        self.set_mmsi(ship.mmsi)

    def refresh(self) -> None:

        if self._mmsi is None:
            self.clear()
            return

        ship = registry.get(self._mmsi)
        try:
            record = vessel_database.get(self._mmsi)
        except Exception:
            logger.exception("Vessel DB lookup failed for %s", self._mmsi)
            record = None

        self._empty_label.setVisible(False)
        for section in self._sections:
            section.setVisible(True)

        name = _coalesce(
            getattr(ship, "name", None) if ship else None,
            getattr(record, "name", None) if record else None,
        )
        callsign = _coalesce(
            getattr(ship, "callsign", None) if ship else None,
            getattr(record, "callsign", None) if record else None,
        )
        ship_type = _coalesce(
            getattr(ship, "ship_type", None) if ship else None,
            getattr(record, "ship_type", None) if record else None,
        )
        imo = _coalesce(
            getattr(ship, "imo", None) if ship else None,
            getattr(record, "imo", None) if record else None,
        )
        flag = _coalesce(
            getattr(ship, "flag", None) if ship else None,
            getattr(record, "flag", None) if record else None,
        )

        self._overview.set_value(self._name, _dash(name or None))
        self._overview.set_value(self._mmsi_value, str(self._mmsi))
        self._overview.set_value(self._imo, _dash(imo or None))
        self._overview.set_value(self._callsign, _dash(callsign or None))
        self._overview.set_value(self._flag, _dash(flag or None))
        self._overview.set_value(self._ship_type, _dash(ship_type or None))
        self._update_flag_image(flag)
        self._update_photo(self._mmsi)

        if ship is not None and (ship.lat or ship.lon):
            lat_text = format_coord(ship.lat)
            lon_text = format_coord(ship.lon)
            speed_text = format_speed(ship.speed)
            course_text = format_angle(ship.course)
            heading_value = ship.heading if ship.heading else ship.course
            heading_text = format_angle(heading_value)
        else:
            lat_text = lon_text = speed_text = course_text = heading_text = "—"

        self._position.set_value(self._lat, lat_text)
        self._position.set_value(self._lon, lon_text)
        self._position.set_value(self._speed, speed_text)
        self._position.set_value(self._course, course_text)
        self._position.set_value(self._heading, heading_text)
        self._position.set_value(self._rot, "—")
        self._position.set_value(self._nav_status, "—")

        destination = _coalesce(
            getattr(ship, "destination", None) if ship else None,
        )
        eta = _coalesce(getattr(ship, "eta", None) if ship else None)
        draft = None
        if ship is not None:
            draft = getattr(ship, "draft", None)
            if draft is None:
                draft = getattr(ship, "draught", None)
        if draft is None and record is not None:
            draft = record.draft

        self._voyage.set_value(self._departure, "—")
        self._voyage.set_value(self._destination, _dash(destination or None))
        self._voyage.set_value(self._eta, _dash(eta or None))
        self._voyage.set_value(
            self._draught,
            format_number(draft, 1) if draft is not None else "—",
        )
        self._voyage.set_value(self._cargo, "—")

        length = getattr(ship, "length", None) if ship else None
        width = getattr(ship, "width", None) if ship else None
        if length is None and record is not None:
            length = record.length
        if width is None and record is not None:
            width = record.width

        length_text = format_number(length, 1)
        width_text = format_number(width, 1)
        self._vessel.set_value(
            self._length,
            f"{length_text} m" if length_text != "—" else "—",
        )
        self._vessel.set_value(
            self._width,
            f"{width_text} m" if width_text != "—" else "—",
        )
        self._vessel.set_value(self._year_built, "—")
        self._vessel.set_value(self._gt, "—")
        self._vessel.set_value(self._dwt, "—")

        last_seen = getattr(ship, "last_seen", None) if ship else None
        if last_seen is None and record is not None:
            last_seen = record.last_seen
        age_text, status_text, status_color = _format_signal_age(last_seen)

        self._live.set_value(self._ais_provider, _dash(_provider_label(ship) or None))
        self._live.set_value(
            self._last_update,
            format_last_seen(last_seen.isoformat() if isinstance(last_seen, datetime) else last_seen),
        )
        self._live.set_value(self._signal_age, age_text)
        self._live.set_value(self._online, tr(status_text), color=status_color)
        self._status_badge.setText(tr(status_text))
        self._status_badge.setStyleSheet(self._badge_style(status_color))

        camera_name = ""
        camera_distance = "—"
        if ship is not None:
            match = camera_selection_engine.get_best_camera(ship)
            if match is not None:
                camera_name = str(getattr(match.camera, "name", "") or "")
                camera_distance = format_distance(match.distance_km)
        self._camera.set_value(self._camera_name, _dash(camera_name or None))
        self._camera.set_value(self._camera_distance, camera_distance)
        # Preview remains a placeholder in the details sheet (live preview stays in CameraPreviewPanel).
        self._camera_box.show_placeholder()

        if record is not None:
            db_status = tr("Found")
            db_color = ThemeColors.Success
            record_id = str(record.mmsi)
        else:
            db_status = tr("Not in local database")
            db_color = ThemeColors.Warning
            record_id = str(self._mmsi)

        last_sync_text = "—"
        try:
            snapshot = vessel_database_manager.collect_snapshot()
            last_sync = snapshot.synchronization.last_sync
            if last_sync is not None:
                last_sync_text = format_last_seen(last_sync.isoformat())
        except Exception:
            logger.exception("Failed to read vessel DB sync state")

        self._database.set_value(self._db_status, db_status, color=db_color)
        self._database.set_value(self._db_last_sync, last_sync_text)
        self._database.set_value(self._db_record_id, record_id)

    def _update_flag_image(self, flag_code: str) -> None:

        self._flag_image.clear()
        if not flag_code:
            return

        try:
            path = flag_manager.get_flag_file(flag_code)
        except Exception:
            path = None

        if path is None or not Path(path).is_file():
            return

        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return

        self._flag_image.setPixmap(
            pixmap.scaled(
                42,
                28,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _update_photo(self, mmsi: int) -> None:

        try:
            path = photo_manager.get_photo_file(mmsi)
        except Exception:
            path = None
        self._photo_box.show_image(path)
