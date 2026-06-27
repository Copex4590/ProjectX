from pathlib import Path

from engines.ais import AISClient, AISParser
from database import registry

api_file = Path.home() / "duna-monitor" / "api_key.txt"

api_key = api_file.read_text().strip()

client = AISClient()
parser = AISParser()

print("📡 Kapcsolódás...")

client.connect(api_key)

print("✅ Kapcsolódva\n")

while True:

    message = client.receive()

    ship = parser.parse(message)

    if ship is None:
        continue

    registry.add(ship)

    print(
        f"{registry.count():4d} | "
        f"{ship.mmsi} | "
        f"{ship.name:25} | "
        f"{ship.speed:5.1f} km/h | "
        f"{ship.lat:.5f} {ship.lon:.5f}"
    )
