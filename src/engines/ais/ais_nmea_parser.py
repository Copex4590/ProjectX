# ============================================================================
# Project X
# AIS NMEA Parser (RTL / AIS-catcher)
# ============================================================================

from collections import deque

_AIS_CHARS = (
    "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_ !\"#$%&'()*+,-./0123456789:;<=>?"
)

_LON_NOT_AVAILABLE = 181000
_LAT_NOT_AVAILABLE = 91000
_SOG_NOT_AVAILABLE = 1023
_COG_NOT_AVAILABLE = 3600


def _decode_sixbit_char(char):

    value = ord(char) - 48
    if value > 40:
        value -= 8
    return value & 0x3F


def _payload_to_bits(payload, fill_bits=0):

    bits = []

    for char in payload:
        value = _decode_sixbit_char(char)
        for shift in range(5, -1, -1):
            bits.append((value >> shift) & 1)

    if fill_bits:
        bits = bits[:-fill_bits]

    return bits


def _bits_to_int(bits, start, length):

    value = 0
    for bit in bits[start:start + length]:
        value = (value << 1) | bit
    return value


def _bits_to_signed(bits, start, length):

    value = _bits_to_int(bits, start, length)
    if value & (1 << (length - 1)):
        value -= 1 << length
    return value


def _decode_text(bits, start, length):

    text = []

    for offset in range(start, start + length, 6):
        index = _bits_to_int(bits, offset, 6)
        if index == 0:
            break
        if index < len(_AIS_CHARS):
            text.append(_AIS_CHARS[index])

    return "".join(text).rstrip("@").strip()


def _parse_nmea_line(line):

    line = line.strip()

    if not line.startswith(("!AIVDM", "!AIVDO")):
        return None

    parts = line.split(",")

    if len(parts) < 7:
        return None

    try:
        total_fragments = int(parts[1])
        fragment_number = int(parts[2])
        fill_bits = int(parts[6].split("*", 1)[0])
    except ValueError:
        return None

    message_id = parts[3]
    channel = parts[4]
    payload = parts[5]

    return (
        total_fragments,
        fragment_number,
        message_id,
        channel,
        payload,
        fill_bits,
    )


def _decode_position(bits, message_type):

    mmsi = _bits_to_int(bits, 8, 30)

    sog_raw = _bits_to_int(bits, 50, 10)
    sog = sog_raw / 10.0 if sog_raw != _SOG_NOT_AVAILABLE else 0.0

    lon_raw = _bits_to_signed(bits, 61, 28)
    lon = lon_raw / 600000.0 if lon_raw != _LON_NOT_AVAILABLE else None

    lat_raw = _bits_to_signed(bits, 89, 27)
    lat = lat_raw / 600000.0 if lat_raw != _LAT_NOT_AVAILABLE else None

    cog_raw = _bits_to_int(bits, 116, 12)
    cog = cog_raw / 10.0 if cog_raw != _COG_NOT_AVAILABLE else 0.0

    return {
        "id": message_type,
        "mmsi": mmsi,
        "x": lon,
        "y": lat,
        "sog": sog,
        "cog": cog,
    }


def _decode_type_18(bits):

    mmsi = _bits_to_int(bits, 8, 30)

    sog_raw = _bits_to_int(bits, 46, 10)
    sog = sog_raw / 10.0 if sog_raw != _SOG_NOT_AVAILABLE else 0.0

    lon_raw = _bits_to_signed(bits, 57, 28)
    lon = lon_raw / 600000.0 if lon_raw != _LON_NOT_AVAILABLE else None

    lat_raw = _bits_to_signed(bits, 85, 27)
    lat = lat_raw / 600000.0 if lat_raw != _LAT_NOT_AVAILABLE else None

    cog_raw = _bits_to_int(bits, 112, 12)
    cog = cog_raw / 10.0 if cog_raw != _COG_NOT_AVAILABLE else 0.0

    return {
        "id": 18,
        "mmsi": mmsi,
        "x": lon,
        "y": lat,
        "sog": sog,
        "cog": cog,
    }


def _decode_type_5(bits):

    mmsi = _bits_to_int(bits, 8, 30)
    callsign = _decode_text(bits, 70, 42)
    name = _decode_text(bits, 112, 120)
    ship_type = _bits_to_int(bits, 232, 8)
    dim_bow = _bits_to_int(bits, 240, 9)
    dim_stern = _bits_to_int(bits, 249, 9)
    dim_port = _bits_to_int(bits, 258, 6)
    dim_starboard = _bits_to_int(bits, 264, 6)
    eta_month = _bits_to_int(bits, 274, 4)
    eta_day = _bits_to_int(bits, 278, 5)
    eta_hour = _bits_to_int(bits, 283, 5)
    eta_minute = _bits_to_int(bits, 288, 6)
    draught_raw = _bits_to_int(bits, 294, 8)
    destination = _decode_text(bits, 302, 120)

    draught = draught_raw / 10.0 if draught_raw else ""

    return {
        "id": 5,
        "mmsi": mmsi,
        "name": name,
        "callsign": callsign,
        "destination": destination,
        "eta_month": eta_month,
        "eta_day": eta_day,
        "eta_hour": eta_hour,
        "eta_minute": eta_minute,
        "draught": draught,
        "ship_type": ship_type,
        "dim_bow": dim_bow,
        "dim_stern": dim_stern,
        "dim_port": dim_port,
        "dim_starboard": dim_starboard,
    }


def _decode_bits(bits):

    if len(bits) < 38:
        return None

    message_type = _bits_to_int(bits, 0, 6)

    if message_type in (1, 2, 3):
        return _decode_position(bits, message_type)

    if message_type == 5:
        return _decode_type_5(bits)

    if message_type == 18:
        return _decode_type_18(bits)

    return None


class AisNmeaParser:

    def __init__(self):

        self._fragments = {}
        self._decoded = deque()

    def feed(self, line):

        parsed = _parse_nmea_line(line)

        if parsed is None:
            return

        (
            total_fragments,
            fragment_number,
            message_id,
            channel,
            payload,
            fill_bits,
        ) = parsed

        if total_fragments == 1:
            bits = _payload_to_bits(payload, fill_bits)
            decoded = _decode_bits(bits)
            if decoded is not None:
                self._decoded.append(decoded)
            return

        key = (message_id, channel)
        entry = self._fragments.get(key)

        if entry is None:
            entry = {
                "total": total_fragments,
                "parts": {},
            }
            self._fragments[key] = entry

        entry["parts"][fragment_number] = payload

        if fragment_number == total_fragments:
            entry["fill_bits"] = fill_bits

        if len(entry["parts"]) != total_fragments:
            return

        full_payload = "".join(
            entry["parts"][index]
            for index in range(1, total_fragments + 1)
        )
        fill = entry.get("fill_bits", 0)
        del self._fragments[key]

        bits = _payload_to_bits(full_payload, fill)
        decoded = _decode_bits(bits)

        if decoded is not None:
            self._decoded.append(decoded)

    def pop_decoded(self):

        if not self._decoded:
            return None

        return self._decoded.popleft()
