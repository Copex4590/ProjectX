import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path

import websocket

from ais.ais_manager import ais_api_key_file
from ais.providers import AISProviderType, normalize_provider_type
from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from app.paths import is_frozen
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
from observation.observation_manager import observation_points_file
from preferences import preferences_manager
from preferences.preferences import PREFERENCES_FILE
from storage.deferred_paths import deferred_cache_path

logger = logging.getLogger(__name__)


def ship_cache_file() -> Path:
    """Return the active ship name cache file path."""

    return deferred_cache_path("PROJECTX_SHIP_CACHE_FILE", "ship_cache.json")


def _runtime_export_dir() -> Path:

    from storage import active_export_path

    export_dir = active_export_path()
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir


def _deli_hajok_dir() -> Path:

    deli_dir = deferred_cache_path("PROJECTX_DELI_HAJOK_DIR", "deli_hajok")
    deli_dir.mkdir(parents=True, exist_ok=True)
    return deli_dir


def _ship_registry():
    from database.ship_registry import get_ship_registry

    return get_ship_registry()


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
        self.last_printed_state = {}

        cache_file = ship_cache_file()

        if cache_file.exists():
            try:
                with cache_file.open(encoding="utf-8") as handle:
                    self.ship_names = json.load(handle)
            except Exception:
                self.ship_names = {}

    def on_start(self):

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

    def _publish_ais_status(self, status: str, *, reason: str = "") -> None:

        normalized = str(status or "offline")
        previous = getattr(self, "_last_ais_status_logged", None)

        if previous != normalized:
            detail = f" ({reason})" if reason else ""
            logger.info("AISStream worker status -> %s%s", normalized, detail)
            self._last_ais_status_logged = normalized

        eventbus.publish("ais.status", status=normalized)

    def _log_aisstream_runtime_context(self, *, phase: str) -> None:

        from ais.user_provider_service import (
            get_enabled_provider_ids,
            is_provider_configured,
        )

        preferences = preferences_manager.get()
        enabled_ids = get_enabled_provider_ids()
        api_key = self._aisstream_api_key()
        boxes = reference_observation_bounding_boxes()
        key_file = ais_api_key_file()

        logger.info(
            "AISStream runtime context [%s]: frozen=%s preferences=%s "
            "observation_points=%s ais_api_key_file=%s enabled=%s "
            "legacy_provider=%s configured=%s key_len=%s reference=%s",
            phase,
            is_frozen(),
            PREFERENCES_FILE,
            observation_points_file(),
            key_file,
            enabled_ids,
            preferences.ais_provider,
            is_provider_configured(AISProviderType.AISSTREAM),
            len(api_key),
            "yes" if boxes else "no",
        )

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

        logger.info(
            "AISStream sync_enabled_providers: enabled=%s want_aisstream=%s want_rtl=%s",
            sorted(enabled),
            want_aisstream,
            want_rtl,
        )
        self._log_aisstream_runtime_context(phase="sync")

        with self._runtime_lock:
            if want_aisstream:
                self._aisstream_active = True
                self._resubscribe_requested = True
            elif self._aisstream_active:
                self._aisstream_active = False
                self._resubscribe_requested = False
                self._publish_ais_status("offline", reason="provider disabled")
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

        removed = _ship_registry().purge_ais_only_ships()

        stale_mmsis = [
            mmsi
            for mmsi, payload in self.radar_data.items()
            if payload.get("source") == "AIS"
        ]

        for mmsi in stale_mmsis:
            self.radar_data.pop(mmsi, None)
            self.last_printed_state.pop(mmsi, None)

        if removed:
            eventbus.publish("ship.updated")

    def purge_ais_only_vessels(self) -> None:

        self._purge_ais_runtime_state()

    def _purge_rtl_runtime_state(self) -> None:

        removed = _ship_registry().purge_rtl_only_ships()

        stale_mmsis = [
            mmsi
            for mmsi, payload in self.radar_data.items()
            if payload.get("source") == "RTL"
        ]

        for mmsi in stale_mmsis:
            self.radar_data.pop(mmsi, None)
            self.last_printed_state.pop(mmsi, None)

        if removed:
            eventbus.publish("ship.updated")

    def _aisstream_api_key(self) -> str:

        key = preferences_manager.get().aisstream_api_key.strip()

        if key:
            logger.debug(
                "AISStream API key loaded from preferences (len=%s)", len(key)
            )
            return key

        for path in (ais_api_key_file(),):
            try:
                if path.exists():
                    value = path.read_text(encoding="utf-8").strip()

                    if value:
                        logger.info(
                            "AISStream API key loaded from file %s (len=%s)",
                            path,
                            len(value),
                        )
                        return value

                    logger.warning("AISStream API key file is empty: %s", path)
            except OSError:
                logger.warning("Failed to read AIS API key file: %s", path)

        logger.warning(
            "AISStream API key missing in preferences and %s",
            ais_api_key_file(),
        )
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

        self._publish_ais_status("offline", reason="engine stopped")
        eventbus.publish("rtl.status", status="offline")

        print("🛑 Hybrid Engine stopped")

    def on_observation_changed(self) -> None:

        removed = _ship_registry().purge_outside_reference_coverage()
        if removed:
            print(f"🧹 Removed {removed} ship(s) outside reference coverage")

        if not self._aisstream_enabled():
            return

        with self._runtime_lock:
            self._resubscribe_requested = True

    def _close_ws(self) -> None:

        with self._ws_lock:
            if self._ws:
                try:
                    self._ws.close()
                except Exception:
                    pass
                self._ws = None

    def save_ship_cache(self):

        try:
            cache_file = ship_cache_file()
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            with cache_file.open("w", encoding="utf-8") as handle:
                json.dump(self.ship_names, handle, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def write_hajo_txt(self, name, distance, direction, heading, sog):

        export_file = _runtime_export_dir() / "hajo.txt"

        with export_file.open("w", encoding="utf-8") as handle:
            handle.write(f"{name}\n")
            handle.write(f"{round(distance, 2)} km-re {direction}\n")
            handle.write(f"{heading}\n")

            if sog >= 0.5:
                handle.write(f"{sog:.1f} csomó\n")
            else:
                handle.write("\n")

    def write_radar_txt(self):

        export_file = _runtime_export_dir() / "radar.txt"

        with export_file.open("w", encoding="utf-8") as handle:
            handle.write("🚢 RADAR\n\n")

            for ship in sorted(
                self.radar_data.values(),
                key=lambda x: x["distance"]
            )[:10]:
                handle.write(
                    f'{ship["name"][:20]:20} '
                    f'{ship["distance"]:.2f} km '
                    f'{ship["direction"]}\n'
                )

    def write_radar_kml(self):

        export_file = _runtime_export_dir() / "radar.kml"

        with export_file.open("w", encoding="utf-8") as kml:
            kml.write("""<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document>
""")

            for ship in self.radar_data.values():
                static = self.static_ship_data.get(ship["mmsi"], {})
                age_minutes = int(
                    (datetime.now() - ship["last_seen"]).total_seconds() / 60
                )

                if age_minutes < 60:
                    age_text = f"{age_minutes} perce"
                else:
                    age_text = (
                        f"{age_minutes // 60} órája {age_minutes % 60} perce"
                    )

                kml.write(f"""
<Placemark>
    <name>{ship["name"]}</name>
    <description>
{age_text}
&#10;Távolság: {ship["distance"]:.2f} km
&#10;Irány: {ship["direction"]}
&#10;Forrás: {ship["source"]}
&#10;MMSI: {static.get("mmsi", "?")}
&#10;Cél: {static.get("destination", "?")}
&#10;ETA: {static.get("eta", "?")}
&#10;Hívójel: {static.get("callsign", "?")}
&#10;Merülés: {static.get("draught", "?")} m
&#10;Hossz: {static.get("length", "?")} m
&#10;Szélesség: {static.get("width", "?")} m
</description>
    <Point>
        <coordinates>{ship["lon"]},{ship["lat"]},0</coordinates>
    </Point>
</Placemark>
""")

            kml.write("""
</Document>
</kml>
""")

    def write_radar_json(self):
        data = []

        for ship in self.radar_data.values():
            if "last_seen" in ship:
                if (datetime.now() - ship["last_seen"]).total_seconds() > 300:
                    continue

            static = self.static_ship_data.get(ship["mmsi"], {})

            data.append({
                "name": ship["name"],
                "distance": round(ship["distance"], 2),
                "lat": ship["lat"],
                "lon": ship["lon"],
                "mmsi": ship["mmsi"],
                "speed": round(ship["speed"], 1),
                "direction": ship["direction"],
                "source": ship["source"],
                "last_seen": (
                    ship.get("last_seen").strftime("%Y-%m-%d %H:%M:%S")
                    if ship.get("last_seen") else ""
                ),
                "destination": static.get("destination", ""),
                "eta": static.get("eta", ""),
                "callsign": static.get("callsign", ""),
                "draught": static.get("draught", ""),
                "length": static.get("length", ""),
                "width": static.get("width", "")
            })

        with (_runtime_export_dir() / "radar.json").open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def process_position(self, mmsi, lat, lon, sog, cog, source):
        if lat is None or lon is None:
            return

        if not geo_context.is_within_coverage(lat, lon):
            return

        name = sanitize_name(self.ship_names.get(mmsi, ""))
        if not name:
            name = mmsi

        distance = geo_context.distance_km(lat, lon) or 0.0
        direction = get_direction(lat)
        heading = get_heading(cog, sog, direction)
        current_time = datetime.now().strftime("%m.%d - %H:%M")

        self.radar_data[mmsi] = {
            "name": name,
            "distance": round(distance, 2),
            "lat": lat,
            "lon": lon,
            "mmsi": mmsi,
            "speed": sog,
            "direction": direction,
            "source": source,
            "last_seen": datetime.now()
        }

        if direction == "délre":
            deli_file = _deli_hajok_dir() / f"{name}.txt"

            with deli_file.open("a", encoding="utf-8") as handle:
                handle.write(
                    f"{round(distance, 2)} km | {heading} | "
                    f"{round(sog,1)} csomó | {current_time}\n"
                )

        # --------------------------------------------------
        # KIÍRÁSI LOGIKA:
        # mozgó hajó mindig frissül
        # álló hajó csak egyszer, aztán csak ha újra megmozdul
        # --------------------------------------------------
        moving = sog >= 0.5
        prev_state = self.last_printed_state.get(mmsi)

        should_print = False

        if moving:
            should_print = True
            self.last_printed_state[mmsi] = "moving"
        else:
            if prev_state != "stopped":
                should_print = True
                self.last_printed_state[mmsi] = "stopped"

        static = self.static_ship_data.get(mmsi, {})
        mmsi_int = int(mmsi)
        existing = _ship_registry().get(mmsi_int)

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
            print()
            print("════════════════════════════════════")
            print(f"🚢 {name}")
            print(f"📏 Távolság : {round(distance, 2)} km-re {direction}")
            print(f"🧭 {heading}")
            if sog >= 0.5:
                print(f"⚡ {sog:.1f} csomó")
            print(f"🕒 {current_time} [{source}]")
            print("════════════════════════════════════")

            self.write_hajo_txt(name, distance, direction, heading, sog)

        self.write_radar_txt()
        self.write_radar_kml()
        self.write_radar_json()

    # --------------------------------------------------
    # AISSTREAM HÁTTÉRSZÁL
    # - név + statikus adat mindig
    # - pozíció csak akkor használjuk, ha DÉLRE van a kamerától
    # --------------------------------------------------
    def aisstream_worker(self):

        self._log_aisstream_runtime_context(phase="worker-start")

        while self.running:
            if not self._aisstream_enabled():
                self._close_ws()
                self._publish_ais_status("offline", reason="provider inactive")
                time.sleep(1)
                continue

            subscribed_boxes = reference_observation_bounding_boxes()

            if subscribed_boxes is None:
                logger.info(
                    "AISStream waiting for observation reference point "
                    "(file=%s)",
                    observation_points_file(),
                )
                self._publish_ais_status(
                    "waiting",
                    reason="observation reference missing",
                )
                time.sleep(2)
                continue

            api_key = self._aisstream_api_key()

            if not api_key:
                logger.warning("AISStream offline: API key unavailable")
                self._close_ws()
                self._publish_ais_status("offline", reason="missing API key")
                time.sleep(2)
                continue

            try:
                ws_url = f"wss://stream.aisstream.io/v0/stream?apiKey={api_key}"
                logger.info(
                    "AISStream connecting to %s (key_len=%s bbox=%s)",
                    "wss://stream.aisstream.io/v0/stream?apiKey=<redacted>",
                    len(api_key),
                    subscribed_boxes,
                )

                with self._ws_lock:
                    self._ws = websocket.create_connection(ws_url, timeout=10)
                    self._ws.settimeout(1.0)

                logger.info("AISStream WebSocket connected")

                with trace_block("HybridEngine.aisstream_worker.subscribe_message"):
                    subscribe_message = AISProtocol.subscribe_message(
                        api_key,
                        bounding_boxes=subscribed_boxes,
                    )

                logger.info(
                    "AISStream sending subscription "
                    "(message_types=%s bbox_count=%s)",
                    subscribe_message.get("FilterMessageTypes"),
                    len(subscribe_message.get("BoundingBoxes") or []),
                )

                with self._ws_lock:
                    if self._ws is None:
                        continue
                    self._ws.send(json.dumps(subscribe_message))

                self._resubscribe_requested = False
                logger.info("AISStream subscription sent; marking connected")
                self._publish_ais_status("connected", reason="subscription sent")

                while self.running:
                    if not self._aisstream_enabled():
                        break

                    if self._resubscribe_requested:
                        break

                    current_boxes = reference_observation_bounding_boxes()

                    if current_boxes != subscribed_boxes:
                        logger.info(
                            "AISStream observation area changed; resubscribing"
                        )
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
                        print(f"📻 AIS név: {mmsi} -> {meta_name}")

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
                                print(f"🟢 AISStream név: {mmsi} -> {name}")

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

            except Exception as e:
                if not self.running:
                    break
                logger.exception("AISStream connection error: %s", e)
                self._publish_ais_status("offline", reason=f"connection error: {e}")
                time.sleep(5)
            finally:
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

            if not is_port_open(AIS_CATCHER_HOST, AIS_CATCHER_PORT):
                logger.warning(
                    "AIS-Catcher unavailable on %s:%s — RTL AIS provider disabled",
                    AIS_CATCHER_HOST,
                    AIS_CATCHER_PORT,
                )
                eventbus.publish("rtl.status", status="offline")
                time.sleep(5)
                continue

            print("🚢 Hybrid Duna Monitor")
            print("📡 Kapcsolódás AIS-catcherhez...")

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

            print("✅ Kapcsolódva")
            eventbus.publish("rtl.status", status="connected")

            decoder = AISNmeaDecoder()

            print("📡 Várakozás hajóadatokra...")

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
                                print(f"📻 RÁDIÓ NÉV: {mmsi} -> {ship_name}")

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

                except Exception as e:
                    print("⚠️ RTL hiba:", e)

            self._disconnect_rtl_client()
