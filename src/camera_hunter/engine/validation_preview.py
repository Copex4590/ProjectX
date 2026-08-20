"""Temporary VALIDATED-camera preview: read-only JSON + clickable Leaflet map.

Does not write hunter_catalog_validation.json and does not start catalog scan.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from camera_hunter.engine.catalog_validation import ValidationRecord, ValidationStatus
from camera_hunter.engine.validation_map import validated_map_cameras

AUTO_REFRESH_MS = 30_000


def load_validation_payload(path: Path) -> dict[str, Any]:
    """Read the catalog-validation JSON. Never opens the file for writing."""

    target = Path(path)
    with target.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        return {"cameras": []}
    return payload


def validated_records_from_payload(payload: Mapping[str, Any]) -> list[ValidationRecord]:
    """Keep only cameras whose status field is VALIDATED."""

    records: list[ValidationRecord] = []
    for item in payload.get("cameras") or []:
        if not isinstance(item, dict):
            continue
        record = ValidationRecord.from_dict(item)
        if record.status != ValidationStatus.VALIDATED:
            continue
        if not record.camera_id:
            continue
        records.append(record)
    return records


def load_validated_records(path: Path) -> list[ValidationRecord]:
    """Load VALIDATED cameras from the validation JSON (read-only)."""

    return validated_records_from_payload(load_validation_payload(path))


def records_by_id(records: list[ValidationRecord]) -> dict[str, ValidationRecord]:

    return {record.camera_id: record for record in records if record.camera_id}


def web_url_for_validated_camera(
    index: Mapping[str, ValidationRecord], camera_id: str
) -> str:
    """Same URL the PX map click would give Hunter: listing page ``web_url``."""

    record = index.get(str(camera_id or "").strip())
    if record is None or record.status != ValidationStatus.VALIDATED:
        return ""
    return str(record.web_url or "").strip()


def render_preview_map_html(cameras: list[dict]) -> str:
    """Leaflet map. Marker click calls bridge.selectCamera (same slot as PX)."""

    payload = json.dumps(cameras, ensure_ascii=True)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Project X — validated camera check</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="qrc:///qtwebchannel/qwebchannel.js"></script>
  <style>
    html, body, #map {{ height: 100%; margin: 0; background: #1b2430; }}
    .px-tooltip {{ font: 13px/1.35 sans-serif; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    let cameras = {payload};
    let bridge = null;
    let pendingCameraId = null;
    const markers = [];
    const map = L.map("map").setView([20, 0], 2);
    L.tileLayer("https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png", {{
      maxZoom: 19,
      attribution: "&copy; OpenStreetMap"
    }}).addTo(map);
    const group = L.featureGroup().addTo(map);

    function reportCamera(cameraId) {{
      const id = String(cameraId || "");
      if (!id) return;
      if (bridge && typeof bridge.selectCamera === "function") {{
        bridge.selectCamera(id);
        pendingCameraId = null;
        return;
      }}
      pendingCameraId = id;
    }}

    function clearMarkers() {{
      markers.forEach(function (marker) {{ group.removeLayer(marker); }});
      markers.length = 0;
    }}

    function addMarkers(list) {{
      clearMarkers();
      (list || []).forEach(function (camera) {{
        const marker = L.marker([camera.lat, camera.lon]);
        marker.bindTooltip(
          '<div class="px-tooltip"><strong>' +
          (camera.name || camera.id) +
          "</strong><div>" + (camera.id || "") + "</div></div>",
          {{ direction: "top" }}
        );
        marker.on("click", function () {{ reportCamera(camera.id); }});
        marker.addTo(group);
        markers.push(marker);
      }});
      if (markers.length) {{
        map.fitBounds(group.getBounds().pad(0.2));
      }}
    }}

    function updateCameras(next) {{
      cameras = next || [];
      addMarkers(cameras);
    }}

    addMarkers(cameras);

    if (typeof qt !== "undefined" && qt.webChannelTransport) {{
      new QWebChannel(qt.webChannelTransport, function (channel) {{
        bridge = channel.objects.bridge;
        if (pendingCameraId) reportCamera(pendingCameraId);
      }});
    }}
  </script>
</body>
</html>
"""


def preview_map_html_from_records(records: list[ValidationRecord]) -> str:

    return render_preview_map_html(validated_map_cameras(records))
