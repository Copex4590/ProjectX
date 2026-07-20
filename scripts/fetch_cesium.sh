#!/usr/bin/env bash
# Fetch CesiumJS into src/resources/map/cesium/ for offline globe support.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="$ROOT/src/resources/map/cesium"
VERSION="1.143"
ARCHIVE="/tmp/Cesium-${VERSION}.zip"
URL="https://github.com/CesiumGS/cesium/releases/download/${VERSION}/Cesium-${VERSION}.zip"

rm -rf "$TARGET"
mkdir -p "$TARGET"

curl -fsSL "$URL" -o "$ARCHIVE"
unzip -q "$ARCHIVE" "Build/Cesium/*" -d /tmp/cesium-extract-$$
mv "/tmp/cesium-extract-$$/Build/Cesium/"* "$TARGET/"
rm -rf "/tmp/cesium-extract-$$" "$ARCHIVE"

echo "Cesium ${VERSION} assets written to $TARGET"
