#!/usr/bin/env bash
# Fetch Leaflet 1.9.4 into src/resources/map/leaflet/ for offline map support.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/src/resources/map/leaflet"
IMAGES="$TARGET/images"
BASE="https://unpkg.com/leaflet@1.9.4/dist"

mkdir -p "$IMAGES"

curl -fsSL "$BASE/leaflet.css" -o "$TARGET/leaflet.css"
curl -fsSL "$BASE/leaflet.js" -o "$TARGET/leaflet.js"
curl -fsSL "$BASE/images/marker-icon.png" -o "$IMAGES/marker-icon.png"
curl -fsSL "$BASE/images/marker-icon-2x.png" -o "$IMAGES/marker-icon-2x.png"
curl -fsSL "$BASE/images/marker-shadow.png" -o "$IMAGES/marker-shadow.png"
curl -fsSL "$BASE/images/layers.png" -o "$IMAGES/layers.png"
curl -fsSL "$BASE/images/layers-2x.png" -o "$IMAGES/layers-2x.png"

echo "Leaflet assets written to $TARGET"
