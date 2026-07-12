import json
import logging
import math
import os
import subprocess
import threading
import time
from datetime import datetime

import websocket

from config.aiscatcher import AIS_CATCHER_HOST, AIS_CATCHER_PORT
from database import registry
from debug.obs_freeze_trace import trace_block
from engines.ais import AISNmeaDecoder, AISRtlClient
from engines.ais.ais_catcher_launcher import is_port_open
from engines.ais.ais_protocol import AISProtocol
from engines.ais.hybrid_ais_engine import hybrid_ais_engine
from engines.base_engine import BaseEngine
from events import eventbus
from models.ship import Ship

logger = logging.getLogger(__name__)

CAMERA_LAT = 47.501539
CAMERA_LON = 19.039856

BASE_DIR = "/home/zoli/rtl-monitor"
HAJOK_DIR = "/home/zoli/Asztal/Ez a gép/Dunamonitor/Hajók"
DELI_DIR = os.path.join(BASE_DIR, "deli_hajok")
CACHE_FILE = os.path.join(BASE_DIR, "ship_cache.json")
API_KEY_FILE = "/home/zoli/duna-monitor/api_key.txt"
XLSX_SCRIPT = "/home/zoli/duna-monitor/lista_xlsx.py"

os.makedirs(HAJOK_DIR, exist_ok=True)
os.makedirs(DELI_DIR, exist_ok=True)


def sanitize_name(name):
    if not name:
        return ""
    return str(name).replace("@", "").strip()


def calc_distance_km(lat, lon):
    return math.sqrt(
        (lat - CAMERA_LAT) ** 2 +
        (lon - CAMERA_LON) ** 2
    ) * 111


def get_direction(lat):
    return "északra" if lat > CAMERA_LAT else "délre"


def get_heading(cog, sog, direction):
    if sog < 0.5:
        return f"Áll {direction}"
    elif 90 <= cog <= 270:
        return "dél felé halad"
    else:
        return "észak felé halad"


class HybridEngine(BaseEngine):

    def __init__(self):

        super().__init__("RTL Hybrid")

        self.ais_thread = None
        self.rtl_thread = None
        self._rtl_client = None
        self._ws = None

        self.ship_names = {}
        self.static_ship_data = {}
        self.radar_data = {}
        self.last_ship_data = {}
        self.last_printed_state = {}

        # --------------------------------------------------
        # CACHE BETÖLTÉS
        # --------------------------------------------------
        if os.path.exists(CACHE_FILE):
            try:
                with open(CACHE_FILE, "r", encoding="utf-8") as f:
                    self.ship_names = json.load(f)
            except Exception:
                self.ship_names = {}

    def on_start(self):

        self.ais_thread = threading.Thread(
            target=self.aisstream_worker,
            daemon=True,
        )
        self.ais_thread.start()

        if is_port_open(AIS_CATCHER_HOST, AIS_CATCHER_PORT):
            self.rtl_thread = threading.Thread(
                target=self.rtl_worker,
                daemon=True,
            )
            self.rtl_thread.start()
            return

        logger.warning(
            "AIS-Catcher unavailable on %s:%s — RTL AIS provider disabled",
            AIS_CATCHER_HOST,
            AIS_CATCHER_PORT,
        )
        eventbus.publish("rtl.status", status="offline")

    def on_stop(self):

        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass
            self._ws = None

        if self._rtl_client:
            self._rtl_client.disconnect()
            self._rtl_client = None

        eventbus.publish("rtl.status", status="offline")

        print("🛑 Hybrid Engine stopped")

    def save_ship_cache(self):
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.ship_names, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def ensure_ship_folder(self, name):
        ship_dir = os.path.join(HAJOK_DIR, name)

        if not os.path.exists(ship_dir):
            os.makedirs(ship_dir, exist_ok=True)
            print(f"📁 Új hajó dosszié létrehozva: {name}")

            csv_file = os.path.join(ship_dir, "adatlap.csv")
            with open(csv_file, "w", encoding="utf-8") as f:
                f.write(
                    "Időpont;"
                    "Távolság;"
                    "Haladási irány;"
                    "Sebesség;"
                    "Célállomás + ETA;"
                    "Hívójel;"
                    "Merülés;"
                    "MMSI;"
                    "Hajótípus;"
                    "Hossz;"
                    "Szélesség\n"
                )

        return ship_dir

    def write_hajo_txt(self, name, distance, direction, heading, sog):
        with open(os.path.join(BASE_DIR, "hajo.txt"), "w", encoding="utf-8") as f:
            f.write(f"{name}\n")
            f.write(f"{round(distance, 2)} km-re {direction}\n")
            f.write(f"{heading}\n")
            if sog >= 0.5:
                f.write(f"{sog:.1f} csomó\n")
            else:
                f.write("\n")

    def write_radar_txt(self):
        with open(os.path.join(BASE_DIR, "radar.txt"), "w", encoding="utf-8") as rf:
            rf.write("🚢 RADAR\n\n")

            for ship in sorted(
                self.radar_data.values(),
                key=lambda x: x["distance"]
            )[:10]:
                rf.write(
                    f'{ship["name"][:20]:20} '
                    f'{ship["distance"]:.2f} km '
                    f'{ship["direction"]}\n'
                )

    def write_radar_kml(self):
        with open(os.path.join(BASE_DIR, "radar.kml"), "w", encoding="utf-8") as kml:
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

        with open(os.path.join(BASE_DIR, "radar.json"), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def save_csv_row(self, ship_dir, current_time, distance, direction, heading, sog, mmsi):
        csv_file = os.path.join(ship_dir, "adatlap.csv")
        ship_static = self.static_ship_data.get(mmsi, {})

        with open(csv_file, "a", encoding="utf-8") as cf:
            cf.write(
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

        subprocess.run(
            ["python3", XLSX_SCRIPT],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    def process_position(self, mmsi, lat, lon, sog, cog, source):
        if lat is None or lon is None:
            return

        name = sanitize_name(self.ship_names.get(mmsi, ""))
        if not name:
            name = mmsi

        ship_dir = self.ensure_ship_folder(name)

        distance = calc_distance_km(lat, lon)
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
            with open(
                os.path.join(DELI_DIR, f"{name}.txt"), "a", encoding="utf-8"
            ) as df:
                df.write(
                    f"{round(distance, 2)} km | {heading} | "
                    f"{round(sog,1)} csomó | {current_time}\n"
                )

        current_distance = round(distance, 2)

        if mmsi not in self.last_ship_data:
            self.last_ship_data[mmsi] = {
                "distance": current_distance,
                "speed": sog
            }
            should_save = True
        else:
            last_distance = self.last_ship_data[mmsi]["distance"]
            should_save = (
                abs(current_distance - last_distance) >= 0.01
                or sog >= 0.5
            )

        if should_save:
            self.save_csv_row(
                ship_dir, current_time, distance, direction, heading, sog, mmsi
            )

        self.last_ship_data[mmsi] = {
            "distance": current_distance,
            "speed": sog
        }

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

        while self.running:
            try:
                print("📡 AISStream kapcsolat...")

                with open(API_KEY_FILE, "r") as f:
                    api_key = f.read().strip()

                self._ws = websocket.create_connection(
                    f"wss://stream.aisstream.io/v0/stream?apiKey={api_key}"
                )

                with trace_block("HybridEngine.aisstream_worker.subscribe_message"):
                    subscribe_message = AISProtocol.subscribe_message(api_key)

                self._ws.send(json.dumps(subscribe_message))
                print("✅ AISStream kapcsolódva")
                eventbus.publish("ais.status", status="connected")

                while self.running:
                    message = self._ws.recv()

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
                print("❌ AISStream hiba:", e)
                eventbus.publish("ais.status", status="offline")
                time.sleep(5)
            finally:
                if self._ws:
                    try:
                        self._ws.close()
                    except Exception:
                        pass
                    self._ws = None

    # --------------------------------------------------
    # RTL / AIS-CATCHER FŐSZÁL
    # - rádiós pozíció
    # - ha rádióból jön ID5 / név, azt is eltesszük
    # --------------------------------------------------
    def rtl_worker(self):

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
            eventbus.publish("rtl.status", status="offline")
            return

        print("✅ Kapcsolódva")
        eventbus.publish("rtl.status", status="connected")

        decoder = AISNmeaDecoder()

        print("📡 Várakozás hajóadatokra...")

        while self.running:
            try:
                line = self._rtl_client.receive()
            except OSError:
                if not self.running:
                    break
                eventbus.publish("rtl.status", status="offline")
                raise

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
