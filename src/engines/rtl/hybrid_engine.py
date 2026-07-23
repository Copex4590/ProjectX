import json
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path

import websocket

from ais.ais_manager import AIS_API_KEY_FILE, _LEGACY_API_KEY_FILE
from ais.providers import AISProviderType, normalize_provider_type
from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from database import registry
from debug.obs_freeze_trace import trace_block
from engines.ais import AISNmeaDecoder, AISRtlClient
from engines.ais.ais_catcher_launcher import is_port_open
from engines.ais.ais_protocol import AISProtocol, reference_observation_bounding_boxes
from engines.ais.hybrid_ais_engine import hybrid_ais_engine
from engines.base_engine import BaseEngine
from events import eventbus
from logbook.duna_format import get_direction, get_heading, sanitize_name
from models.ship import Ship
from observation.geo_context import geo_context
from preferences import preferences_manager
from app.paths import ensure_runtime_data_dirs, hybrid_runtime_dir, runtime_data_path
from logbook.paths import HAJOK_DIR as LOGBOOK_HAJOK_DIR
from engines.rtl.hybrid_file_writer import hybrid_file_writer

logger = logging.getLogger(__name__)

# SAVE-202: all HybridEngine runtime files live under the app data directory.
ensure_runtime_data_dirs()
BASE_DIR = str(hybrid_runtime_dir())
HAJOK_DIR = str(LOGBOOK_HAJOK_DIR)
DELI_DIR = str(hybrid_runtime_dir() / "deli_hajok")
CACHE_FILE = str(hybrid_runtime_dir() / "ship_cache.json")
# Legacy absolute API key path removed — use preferences / ais_manager paths only.
API_KEY_FILE = str(runtime_data_path("api_key.txt"))

# SAVE-105: radar file exports are throttled on the AIS/RTL hot path.
RADAR_WRITE_INTERVAL_S = 1.0
THREAD_JOIN_TIMEOUT_S = 5.0
REGISTRY_TTL_SECONDS = 1800
AIS_RECONNECT_MIN_S = 1.0
AIS_RECONNECT_MAX_S = 60.0
AIS_CONNECTION_TIMEOUT_S = 10.0


def _ais_connection_preferences() -> tuple[bool, bool, float, float, float]:

    preferences = preferences_manager.get()
    min_s = max(0.1, float(preferences.ais_reconnect_min_s or AIS_RECONNECT_MIN_S))
    max_s = max(min_s, float(preferences.ais_reconnect_max_s or AIS_RECONNECT_MAX_S))
    timeout_s = max(
        1.0,
        float(preferences.ais_connection_timeout_s or AIS_CONNECTION_TIMEOUT_S),
    )
    return (
        bool(preferences.ais_auto_connect),
        bool(preferences.ais_reconnect_enabled),
        min_s,
        max_s,
        timeout_s,
    )


class HybridEngine(BaseEngine):

    def __init__(self):

        super().__init__("RTL Hybrid")

        self.ais_thread = None
        self.rtl_thread = None
        self._rtl_client = None
        self._ws = None
        self._ws_lock = threading.Lock()
        self._resubscribe_requested = False
        self._runtime_lock = threading.Lock()
        self._aisstream_active = False
        self._rtl_active = False

        self.ship_names = {}
        self.static_ship_data = {}
        self.radar_data = {}
        self.last_ship_data = {}
        self.last_printed_state = {}
        self._last_radar_write_at = 0.0

        # --------------------------------------------------
        # CACHE BETÖLTÉS
        # --------------------------------------------------
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.ship_names = json.load(f)
            except Exception:
                logger.exception("Failed to load ship name cache from %s", CACHE_FILE)
                self.ship_names = {}

        self._ais_reconnect_backoff_s = AIS_RECONNECT_MIN_S
        self._ais_connect_lock = threading.Lock()
        self._state_lock = threading.RLock()
        hybrid_file_writer.start()

    def on_start(self):

        hybrid_file_writer.start()
        self.sync_enabled_providers()

        if self.ais_thread is None or not self.ais_thread.is_alive():
            self.ais_thread = threading.Thread(
                target=self.aisstream_worker,
                daemon=True,
            )
            self.ais_thread.start()

        if self.rtl_thread is None or not self.rtl_thread.is_alive():
            self.rtl_thread = threading.Thread(
                target=self.rtl_worker,
                daemon=True,
            )
            self.rtl_thread.start()

    def sync_enabled_providers(self, enabled_ids: list[str] | None = None) -> None:

        from ais.user_provider_service import (
            get_enabled_provider_ids,
            is_provider_configured,
        )

        if enabled_ids is None:
            enabled_ids = get_enabled_provider_ids()

        enabled = {
            normalize_provider_type(provider_id) for provider_id in enabled_ids
        }

        want_aisstream = (
            AISProviderType.AISSTREAM in enabled
            and is_provider_configured(AISProviderType.AISSTREAM)
        )
        want_rtl = (
            AISProviderType.LOCAL in enabled
            and is_provider_configured(AISProviderType.LOCAL)
        )

        with self._runtime_lock:
            if want_aisstream:
                self._aisstream_active = True
                self._resubscribe_requested = True
                self._close_ws()
            elif self._aisstream_active:
                self._aisstream_active = False
                self._resubscribe_requested = False
                self._close_ws()
                eventbus.publish("ais.status", status="offline")
                self._purge_ais_runtime_state()

            if want_rtl:
                self._rtl_active = True
            elif self._rtl_active:
                self._rtl_active = False
                self._disconnect_rtl_client()
                eventbus.publish("rtl.status", status="offline")
                self._purge_rtl_runtime_state()

    def _disconnect_rtl_client(self) -> None:

        client = self._rtl_client

        if client is None:
            return

        try:
            client.disconnect()
        except Exception:
            logger.exception("Failed to disconnect RTL AIS client")

        self._rtl_client = None

    def _purge_ais_runtime_state(self) -> None:

        removed = registry.purge_ais_only_ships()

        stale_mmsis = [
            mmsi
            for mmsi, payload in self.radar_data.items()
            if payload.get("source") == "AIS"
        ]

        for mmsi in stale_mmsis:
            self.radar_data.pop(mmsi, None)
            self.last_ship_data.pop(mmsi, None)
            self.last_printed_state.pop(mmsi, None)

        if removed:
            eventbus.publish("ship.updated")

    def purge_ais_only_vessels(self) -> None:

        self._purge_ais_runtime_state()

    def _purge_rtl_runtime_state(self) -> None:

        removed = registry.purge_rtl_only_ships()

        stale_mmsis = [
            mmsi
            for mmsi, payload in self.radar_data.items()
            if payload.get("source") == "RTL"
        ]

        for mmsi in stale_mmsis:
            self.radar_data.pop(mmsi, None)
            self.last_ship_data.pop(mmsi, None)
            self.last_printed_state.pop(mmsi, None)

        if removed:
            eventbus.publish("ship.updated")

    def _aisstream_api_key(self) -> str:

        key = preferences_manager.get().aisstream_api_key.strip()

        if key:
            return key

        for path in (AIS_API_KEY_FILE, _LEGACY_API_KEY_FILE, Path(API_KEY_FILE)):
            try:
                if path.exists():
                    value = path.read_text(encoding="utf-8").strip()

                    if value:
                        return value
            except OSError:
                logger.warning("Failed to read AIS API key file: %s", path)

        return ""

    def _aisstream_enabled(self) -> bool:

        with self._runtime_lock:
            return self._aisstream_active

    def _rtl_enabled(self) -> bool:

        with self._runtime_lock:
            return self._rtl_active

    def on_stop(self):

        with self._runtime_lock:
            self._aisstream_active = False
            self._rtl_active = False

        self._close_ws()
        self._disconnect_rtl_client()

        for label, thread in (
            ("AISStream", self.ais_thread),
            ("RTL", self.rtl_thread),
        ):
            if thread is None or not thread.is_alive():
                continue
            thread.join(timeout=THREAD_JOIN_TIMEOUT_S)
            if thread.is_alive():
                logger.warning(
                    "HybridEngine %s worker did not stop within %.1fs",
                    label,
                    THREAD_JOIN_TIMEOUT_S,
                )

        hybrid_file_writer.stop(timeout=THREAD_JOIN_TIMEOUT_S)

        eventbus.publish("ais.status", status="offline")
        eventbus.publish("rtl.status", status="offline")

        logger.info("Hybrid Engine stopped")

    def on_observation_changed(self) -> None:

        removed = registry.purge_outside_reference_coverage()
        if removed:
            logger.info("Removed %s ship(s) outside reference coverage", removed)

        if not self._aisstream_enabled():
            return

        self._resubscribe_requested = True
        self._close_ws()

    def _close_ws(self) -> None:

        with self._ws_lock:
            if self._ws:
                try:
                    self._ws.close()
                except Exception:
                    logger.debug("AISStream websocket close failed", exc_info=True)
                self._ws = None

    def save_ship_cache(self):
        with self._state_lock:
            names = dict(self.ship_names)
        hybrid_file_writer.enqueue(
            {"kind": "save_cache", "path": CACHE_FILE, "ship_names": names}
        )

    def ensure_ship_folder(self, name):
        ship_dir = os.path.join(HAJOK_DIR, name)
        hybrid_file_writer.enqueue({"kind": "ensure_folder", "ship_dir": ship_dir})
        return ship_dir

    def write_hajo_txt(self, name, distance, direction, heading, sog):
        lines = [
            f"{name}",
            f"{round(distance, 2)} km-re {direction}",
            f"{heading}",
            f"{sog:.1f} csomó" if sog >= 0.5 else "",
            "",
        ]
        hybrid_file_writer.enqueue(
            {
                "kind": "write_hajo",
                "path": os.path.join(BASE_DIR, "hajo.txt"),
                "text": "\n".join(lines),
            }
        )

    def _radar_payload(self, ship: dict, static: dict) -> dict:
        last_seen = ship.get("last_seen")
        return {
            "name": ship["name"],
            "distance": round(ship["distance"], 2),
            "lat": ship["lat"],
            "lon": ship["lon"],
            "mmsi": ship["mmsi"],
            "speed": round(float(ship.get("speed", 0) or 0), 1),
            "direction": ship["direction"],
            "source": ship["source"],
            "last_seen": (
                last_seen.strftime("%Y-%m-%d %H:%M:%S") if last_seen else ""
            ),
            "destination": static.get("destination", ""),
            "eta": static.get("eta", ""),
            "callsign": static.get("callsign", ""),
            "draught": static.get("draught", ""),
            "length": static.get("length", ""),
            "width": static.get("width", ""),
        }

    def _enqueue_radar_upsert(self, mmsi: str) -> None:
        with self._state_lock:
            ship = self.radar_data.get(mmsi)
            if ship is None:
                return
            static = self.static_ship_data.get(mmsi, {})
            payload = self._radar_payload(ship, static)
        hybrid_file_writer.enqueue(
            {
                "kind": "radar_upsert",
                "base_dir": BASE_DIR,
                "mmsi": mmsi,
                "payload": payload,
            }
        )

    def _maybe_write_radar_files(self) -> None:
        now = time.monotonic()
        if (now - self._last_radar_write_at) < RADAR_WRITE_INTERVAL_S:
            return
        self._last_radar_write_at = now
        self._purge_stale_radar_locked()
        hybrid_file_writer.enqueue(
            {"kind": "radar_flush", "base_dir": BASE_DIR, "force_full_kml": False}
        )

    def _purge_stale_radar_locked(self) -> None:
        now = datetime.now()
        stale = []
        with self._state_lock:
            for mmsi, ship in list(self.radar_data.items()):
                last_seen = ship.get("last_seen")
                if last_seen is None:
                    continue
                age = (now - last_seen).total_seconds()
                if age > REGISTRY_TTL_SECONDS:
                    stale.append(mmsi)
            for mmsi in stale:
                self.radar_data.pop(mmsi, None)
                self.last_ship_data.pop(mmsi, None)
                self.last_printed_state.pop(mmsi, None)
        for mmsi in stale:
            hybrid_file_writer.enqueue({"kind": "radar_remove", "mmsi": mmsi})
        if stale:
            registry.purge_idle(REGISTRY_TTL_SECONDS)
            for mmsi in stale:
                try:
                    registry.remove(int(mmsi))
                except Exception:
                    logger.debug(
                        "Failed to purge stale registry MMSI %s",
                        mmsi,
                        exc_info=True,
                    )

    def save_csv_row(self, ship_dir, current_time, distance, direction, heading, sog, mmsi):
        with self._state_lock:
            ship_static = dict(self.static_ship_data.get(mmsi, {}))
        row = (
            f"{current_time};"
            f"{round(distance, 2)} km {direction};"
            f"{heading};"
            f"{'' if sog < 0.5 else str(round(sog, 1)) + ' csomó'};"
            f"{ship_static.get('destination', '')} {ship_static.get('eta', '')};"
            f"{ship_static.get('callsign', '')};"
            f"{ship_static.get('draught', '')};"
            f"{ship_static.get('mmsi', mmsi)};"
            f"{ship_static.get('type', '')};"
            f"{ship_static.get('length', '')};"
            f"{ship_static.get('width', '')}\n"
        )
        hybrid_file_writer.enqueue(
            {"kind": "append_csv", "ship_dir": ship_dir, "row": row}
        )

    def process_position(self, mmsi, lat, lon, sog, cog, source):
        if lat is None or lon is None:
            return

        if not geo_context.is_within_coverage(lat, lon):
            return

        with self._state_lock:
            name = sanitize_name(self.ship_names.get(mmsi, ""))
        if not name:
            name = mmsi

        ship_dir = self.ensure_ship_folder(name)

        distance = geo_context.distance_km(lat, lon) or 0.0
        direction = get_direction(lat)
        heading = get_heading(cog, sog, direction)
        current_time = datetime.now().strftime("%m.%d - %H:%M")

        with self._state_lock:
            self.radar_data[mmsi] = {
                "name": name,
                "distance": round(distance, 2),
                "lat": lat,
                "lon": lon,
                "mmsi": mmsi,
                "speed": sog,
                "direction": direction,
                "source": source,
                "last_seen": datetime.now(),
            }

        self._enqueue_radar_upsert(mmsi)

        if direction == "délre":
            hybrid_file_writer.enqueue(
                {
                    "kind": "append_deli",
                    "path": os.path.join(DELI_DIR, f"{name}.txt"),
                    "row": (
                        f"{round(distance, 2)} km | {heading} | "
                        f"{round(sog,1)} csomó | {current_time}\n"
                    ),
                }
            )

        current_distance = round(distance, 2)

        with self._state_lock:
            if mmsi not in self.last_ship_data:
                self.last_ship_data[mmsi] = {
                    "distance": current_distance,
                    "speed": sog,
                }
                should_save = True
            else:
                last_distance = self.last_ship_data[mmsi]["distance"]
                should_save = (
                    abs(current_distance - last_distance) >= 0.01
                    or sog >= 0.5
                )

            self.last_ship_data[mmsi] = {
                "distance": current_distance,
                "speed": sog,
            }

            moving = sog >= 0.5
            prev_state = self.last_printed_state.get(mmsi)
            should_print = False
            if moving:
                should_print = True
                self.last_printed_state[mmsi] = "moving"
            elif prev_state != "stopped":
                should_print = True
                self.last_printed_state[mmsi] = "stopped"

            static = dict(self.static_ship_data.get(mmsi, {}))

        if should_save:
            self.save_csv_row(
                ship_dir, current_time, distance, direction, heading, sog, mmsi
            )

        mmsi_int = int(mmsi)
        existing = registry.get(mmsi_int)

        ship = Ship(
            mmsi=mmsi_int,
            name=str(name),
            callsign=static.get("callsign", ""),
            ship_type=str(static.get("type", "")),
            lat=lat,
            lon=lon,
            speed=sog,
            course=cog,
            heading=cog,
            destination=static.get("destination", ""),
            eta=static.get("eta", ""),
            source=source,
            distance_km=round(distance, 2),
            direction=direction,
            text_heading=heading,
            last_seen=datetime.now(),
            ais_visible=(
                source == "AIS"
                or (existing.ais_visible if existing else False)
            ),
            rtl_visible=(
                source == "RTL"
                or (existing.rtl_visible if existing else False)
            ),
        )

        hybrid_ais_engine.publish_ship(ship)

        if should_print:
            logger.debug(
                "Ship update %s dist=%.2f km %s heading=%s sog=%.1f [%s]",
                name,
                distance,
                direction,
                heading,
                sog,
                source,
            )
            self.write_hajo_txt(name, distance, direction, heading, sog)

        self._maybe_write_radar_files()

    # --------------------------------------------------
    # AISSTREAM HÁTTÉRSZÁL
    # - név + statikus adat mindig
    # - pozíció csak akkor használjuk, ha DÉLRE van a kamerától
    # --------------------------------------------------
    def aisstream_worker(self):

        while self.running:
            if not self._aisstream_enabled():
                self._close_ws()
                eventbus.publish("ais.status", status="offline")
                time.sleep(1)
                continue

            subscribed_boxes = reference_observation_bounding_boxes()

            if subscribed_boxes is None:
                logger.info("Waiting for observation reference point before AISStream")
                eventbus.publish("ais.status", status="waiting")
                time.sleep(2)
                continue

            api_key = self._aisstream_api_key()

            if not api_key:
                logger.info("AISStream disabled or missing API key")
                self._close_ws()
                eventbus.publish("ais.status", status="offline")
                time.sleep(2)
                continue

            auto_connect, reconnect_enabled, reconnect_min, reconnect_max, timeout_s = (
                _ais_connection_preferences()
            )

            if not auto_connect:
                self._close_ws()
                eventbus.publish("ais.status", status="offline")
                time.sleep(1)
                continue

            if not self._ais_connect_lock.acquire(blocking=False):
                time.sleep(0.2)
                continue

            try:
                logger.info("Connecting to AISStream")

                with self._ws_lock:
                    self._ws = websocket.create_connection(
                        f"wss://stream.aisstream.io/v0/stream?apiKey={api_key}",
                        timeout=timeout_s,
                    )
                    self._ws.settimeout(1.0)

                with trace_block("HybridEngine.aisstream_worker.subscribe_message"):
                    subscribe_message = AISProtocol.subscribe_message(
                        api_key,
                        bounding_boxes=subscribed_boxes,
                    )

                with self._ws_lock:
                    if self._ws is None:
                        continue
                    self._ws.send(json.dumps(subscribe_message))

                self._resubscribe_requested = False
                self._ais_reconnect_backoff_s = reconnect_min
                logger.info("AISStream connected")
                eventbus.publish("ais.status", status="connected")

                while self.running:
                    if not self._aisstream_enabled():
                        break

                    if self._resubscribe_requested:
                        break

                    current_boxes = reference_observation_bounding_boxes()

                    if current_boxes != subscribed_boxes:
                        logger.info("Observation area changed — resubscribing AISStream")
                        break

                    try:
                        with self._ws_lock:
                            if self._ws is None:
                                break
                            message = self._ws.recv()
                    except websocket.WebSocketTimeoutException:
                        continue

                    if isinstance(message, bytes):
                        message = message.decode("utf-8")

                    data = json.loads(message)

                    if "MetaData" not in data:
                        continue

                    mmsi = str(data["MetaData"].get("MMSI", ""))
                    if not mmsi:
                        continue

                    # ---- név a MetaData-ból, ha van ----
                    meta_name = sanitize_name(
                        data["MetaData"].get("ShipName", "")
                    )
                    if meta_name and self.ship_names.get(mmsi) != meta_name:
                        self.ship_names[mmsi] = meta_name
                        self.save_ship_cache()
                        logger.debug("AIS name %s -> %s", mmsi, meta_name)

                    # ---- PositionReport ----
                    if "PositionReport" in data.get("Message", {}):
                        pos = data["Message"]["PositionReport"]

                        lat = pos.get("Latitude")
                        lon = pos.get("Longitude")
                        sog = float(pos.get("Sog", 0) or 0)
                        cog = float(pos.get("Cog", 0) or 0)

                        if lat is not None and lon is not None:
                            self.process_position(
                                mmsi, lat, lon, sog, cog, "AIS"
                            )

                    # ---- ShipStaticData / StaticDataReport ----
                    ship = None

                    if "ShipStaticData" in data.get("Message", {}):
                        ship = data["Message"]["ShipStaticData"]
                    elif "StaticDataReport" in data.get("Message", {}):
                        ship = data["Message"]["StaticDataReport"]

                    if ship:
                        name = sanitize_name(ship.get("Name", ""))
                        if name:
                            old_name = self.ship_names.get(mmsi, "")
                            self.ship_names[mmsi] = name

                            if old_name != name:
                                self.save_ship_cache()
                                logger.debug("AISStream static name %s -> %s", mmsi, name)

                        self.static_ship_data[mmsi] = {
                            "destination": sanitize_name(
                                ship.get("Destination", "")
                            ),
                            "eta": (
                                f"{ship['Eta']['Month']:02d}.{ship['Eta']['Day']:02d} "
                                f"{ship['Eta']['Hour']:02d}:{ship['Eta']['Minute']:02d}"
                                if "Eta" in ship else ""
                            ),
                            "callsign": sanitize_name(ship.get("CallSign", "")),
                            "draught": ship.get("MaximumStaticDraught", ""),
                            "mmsi": mmsi,
                            "type": ship.get("Type", ""),
                            "length": (
                                ship.get("Dimension", {}).get("A", 0)
                                + ship.get("Dimension", {}).get("B", 0)
                            ),
                            "width": (
                                ship.get("Dimension", {}).get("C", 0)
                                + ship.get("Dimension", {}).get("D", 0)
                            ),
                        }

            except Exception:
                if not self.running:
                    break
                logger.exception("AISStream connection error")
                eventbus.publish("ais.status", status="offline")
                _, reconnect_enabled, reconnect_min, reconnect_max, _ = (
                    _ais_connection_preferences()
                )

                if not reconnect_enabled:
                    time.sleep(5)
                    self._ais_reconnect_backoff_s = reconnect_min
                else:
                    delay = self._ais_reconnect_backoff_s
                    time.sleep(delay)
                    self._ais_reconnect_backoff_s = min(
                        reconnect_max,
                        max(reconnect_min, delay * 2.0),
                    )
            finally:
                self._ais_connect_lock.release()
                self._close_ws()

    # --------------------------------------------------
    # RTL / AIS-CATCHER FŐSZÁL
    # - rádiós pozíció
    # - ha rádióból jön ID5 / név, azt is eltesszük
    # --------------------------------------------------
    def rtl_worker(self):

        while self.running:
            if not self._rtl_enabled():
                self._disconnect_rtl_client()
                eventbus.publish("rtl.status", status="offline")
                time.sleep(1)
                continue

            auto_connect, _, _, _, _ = _ais_connection_preferences()

            if not auto_connect:
                self._disconnect_rtl_client()
                eventbus.publish("rtl.status", status="offline")
                time.sleep(1)
                continue

            if not is_port_open(AIS_CATCHER_HOST, AIS_CATCHER_PORT):
                logger.warning(
                    "AIS-Catcher unavailable on %s:%s — RTL AIS provider disabled",
                    AIS_CATCHER_HOST,
                    AIS_CATCHER_PORT,
                )
                eventbus.publish("rtl.status", status="offline")
                time.sleep(5)
                continue

            logger.info("Connecting to AIS-catcher")

            self._rtl_client = AISRtlClient()

            try:
                self._rtl_client.connect(AIS_CATCHER_HOST, AIS_CATCHER_PORT)
            except OSError as error:
                logger.warning(
                    "RTL AIS connection failed on %s:%s: %s",
                    AIS_CATCHER_HOST,
                    AIS_CATCHER_PORT,
                    error,
                )
                self._rtl_client = None
                eventbus.publish("rtl.status", status="offline")
                time.sleep(5)
                continue

            logger.info("Connected to AIS-catcher")
            eventbus.publish("rtl.status", status="connected")

            decoder = AISNmeaDecoder()

            logger.debug("Waiting for RTL AIS data")

            while self.running and self._rtl_enabled():
                try:
                    line = self._rtl_client.receive()
                except OSError:
                    if not self.running:
                        break
                    eventbus.publish("rtl.status", status="offline")
                    break

                if not line:
                    continue

                if not line.startswith(("!AIVDM", "!AIVDO")):
                    continue

                try:
                    decoder.feed(line)

                    decoded = decoder.decode()
                    if not decoded:
                        continue

                    msg_type = decoded.get("id", 0)
                    mmsi = str(decoded.get("mmsi", ""))

                    if not mmsi:
                        continue

                    # --------------------------------------------------
                    # RÁDIÓS NÉV / STATIKUS ADAT (ID5)
                    # --------------------------------------------------
                    if msg_type == 5:
                        ship_name = sanitize_name(decoded.get("name", ""))
                        if ship_name:
                            old_name = self.ship_names.get(mmsi, "")
                            self.ship_names[mmsi] = ship_name

                            if old_name != ship_name:
                                self.save_ship_cache()
                                logger.debug("RTL name %s -> %s", mmsi, ship_name)

                        self.static_ship_data[mmsi] = {
                            "destination": sanitize_name(
                                decoded.get("destination", "")
                            ),
                            "eta": (
                                f"{decoded.get('eta_month', 0):02d}."
                                f"{decoded.get('eta_day', 0):02d} "
                                f"{decoded.get('eta_hour', 0):02d}:"
                                f"{decoded.get('eta_minute', 0):02d}"
                            ),
                            "callsign": sanitize_name(
                                decoded.get("callsign", "")
                            ),
                            "draught": decoded.get("draught", ""),
                            "mmsi": mmsi,
                            "type": decoded.get("ship_type", ""),
                            "length": (
                                decoded.get("dim_bow", 0)
                                + decoded.get("dim_stern", 0)
                            ),
                            "width": (
                                decoded.get("dim_port", 0)
                                + decoded.get("dim_starboard", 0)
                            ),
                        }
                        continue

                    # --------------------------------------------------
                    # csak pozíciós üzenetek
                    # --------------------------------------------------
                    if msg_type not in [1, 2, 3, 18]:
                        continue

                    lat = decoded.get("y")
                    lon = decoded.get("x")

                    if lat is None or lon is None:
                        continue

                    sog = float(decoded.get("sog", 0) or 0)
                    cog = float(decoded.get("cog", 0) or 0)

                    self.process_position(mmsi, lat, lon, sog, cog, "RTL")

                except Exception:
                    logger.exception("RTL AIS processing error")

            self._disconnect_rtl_client()
