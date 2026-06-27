from engines.ais import AISParser

sample = {
    "MetaData": {
        "MMSI": 211111111,
        "ShipName": "PROJECT X TEST"
    },
    "Message": {
        "PositionReport": {
            "Latitude": 47.5000,
            "Longitude": 19.0400,
            "Sog": 12.5,
            "Cog": 184.2,
            "TrueHeading": 182
        }
    }
}

parser = AISParser()

ship = parser.parse(sample)

print(ship)
