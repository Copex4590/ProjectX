from engines.base_engine import BaseEngine
import threading


import math

# --- Hybrid Monitor helpers (migration step 1) ---

CAMERA_LAT = 47.501539
CAMERA_LON = 19.039856

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

        self.running = False
        self.ais_thread = None
        self.rtl_thread = None

    def on_start(self):

        self.running = True

        self.ais_thread = threading.Thread(
            target=self.aisstream_worker,
            daemon=True
        )

        self.rtl_thread = threading.Thread(
            target=self.rtl_worker,
            daemon=True
        )

        self.ais_thread.start()
        self.rtl_thread.start()

        print("✅ Hybrid Engine started")

    def on_stop(self):

        self.running = False

        print("🛑 Hybrid Engine stopped")

    def aisstream_worker(self):

        while self.running:
            # TODO: ide kerül a Hybrid Monitor aisstream_worker()
            # jelenleg csak életjel
            print("📡 AISStream worker aktív")
            break

    def rtl_worker(self):

        while self.running:
            # TODO: ide kerül az AIS-catcher ciklus
            print("📡 RTL worker aktív")
            break

    def process_position(self, *args, **kwargs):

        pass