"""Standalone Leaflet map of VALIDATED Hunter cameras only."""

from __future__ import annotations

import json
from pathlib import Path

from camera_hunter.engine.catalog_validation import ValidationRecord, ValidationStatus


def validated_map_cameras(records: list[ValidationRecord]) -> list[dict]:
    """Keep VALIDATED cameras that have a usable lat/lon."""

    markers: list[dict] = []
    for record in records or []:
        if record.status != ValidationStatus.VALIDATED:
            continue
        try:
            lat = float(record.lat or 0.0)
            lon = float(record.lon or 0.0)
        except (TypeError, ValueError):
            continue
        if lat == 0.0 and lon == 0.0:
            continue
        markers.append(
            {
                "id": record.camera_id,
                "name": record.name or record.camera_id,
                "lat": lat,
                "lon": lon,
                "country": record.country,
                "location": record.location or record.city,
                "status": record.status.value,
                "web_url": record.web_url,
                "stream_url": record.stream_url,
                "source_type": record.source_type,
            }
        )
    return markers


def render_validated_map_html(cameras: list[dict]) -> str:
    """Self-contained HTML. Leaflet comes from a CDN so file:// works."""

    payload = json.dumps(cameras, ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Project X — validated Hunter cameras</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; }}
    .px-popup {{ font: 14px/1.4 sans-serif; min-width: 180px; }}
    .px-popup a {{ word-break: break-all; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const cameras = {payload};
    const map = L.map("map").setView([20, 0], 2);
    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap"
    }}).addTo(map);

    const group = L.featureGroup();
    cameras.forEach(function (camera) {{
      const marker = L.marker([camera.lat, camera.lon]);
      const place = camera.location || camera.country || "";
      const web = camera.web_url
        ? '<div><a href="' + camera.web_url + '" target="_blank" rel="noopener">' +
          camera.web_url + "</a></div>"
        : "";
      marker.bindPopup(
        '<div class="px-popup">' +
          "<strong>" + (camera.name || camera.id) + "</strong>" +
          (place ? "<div>" + place + "</div>" : "") +
          "<div>" + camera.lat.toFixed(5) + ", " + camera.lon.toFixed(5) + "</div>" +
          "<div>Status: " + (camera.status || "") + "</div>" +
          web +
        "</div>"
      );
      marker.addTo(group);
    }});
    if (cameras.length) {{
      group.addTo(map);
      map.fitBounds(group.getBounds().pad(0.2));
    }}
  </script>
</body>
</html>
"""


def write_validated_map(path: Path, records: list[ValidationRecord]) -> Path:

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    html = render_validated_map_html(validated_map_cameras(records))
    target.write_text(html, encoding="utf-8")
    return target
