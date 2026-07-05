#!/usr/bin/env bash
# ============================================================================
# Project X — Verify Linux release packages (SAVE-077)
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-python3}"
RELEASE_DIR="${ROOT}/release/linux"
CHECKSUM_DIR="${ROOT}/release/checksums"
FAILED=0

read_names() {
    VERSION="$("$PYTHON" - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))
from version import PROJECT_VERSION
print(PROJECT_VERSION)
PY
)"
    APPIMAGE="${RELEASE_DIR}/ProjectX-${VERSION}-x86_64.AppImage"
    DEB="${RELEASE_DIR}/projectx_${VERSION}_amd64.deb"
}

fail() {
    echo "[FAIL] $*"
    FAILED=1
}

ok() {
    echo "[OK] $*"
}

echo "Verifying Linux release packages under ${RELEASE_DIR}..."
read_names

if [[ ! -f "$APPIMAGE" ]]; then
    fail "AppImage not found: $APPIMAGE (run ./scripts/build_linux_release.sh)"
    exit 1
fi

[[ -x "$APPIMAGE" ]] && ok "AppImage is executable" || fail "AppImage is not executable"

EXTRACT="$(mktemp -d)"
trap 'rm -rf "$EXTRACT"' EXIT
cd "$EXTRACT"
"$APPIMAGE" --appimage-extract >/dev/null

for path in \
    squashfs-root/AppRun \
    squashfs-root/projectx.desktop \
    squashfs-root/projectx.png \
    squashfs-root/usr/lib/projectx/projectx \
    squashfs-root/usr/lib/projectx/resources/translations/en.json \
    squashfs-root/usr/lib/projectx/resources/translations/hu.json \
    squashfs-root/usr/lib/projectx/resources/map/leaflet/leaflet.js \
    squashfs-root/usr/lib/projectx/resources/branding/projectx-logo.png \
    squashfs-root/usr/lib/projectx/config/playback.json; do
    [[ -e "$path" ]] && ok "Present: $path" || fail "Missing: $path"
done

[[ -x squashfs-root/AppRun ]] && ok "AppRun executable permission" || fail "AppRun not executable"
[[ -x squashfs-root/usr/lib/projectx/projectx ]] && ok "Application executable permission" || fail "projectx not executable"

if grep -q '^Exec=AppRun' squashfs-root/projectx.desktop; then
    ok "Desktop launcher uses AppRun"
else
    fail "Desktop file missing Exec=AppRun"
fi

if grep -q '^Icon=projectx' squashfs-root/projectx.desktop; then
    ok "Desktop icon entry configured"
else
    fail "Desktop file missing Icon=projectx"
fi

if [[ -f "$DEB" ]]; then
    DEB_EXTRACT="$(mktemp -d)"
    dpkg-deb -x "$DEB" "$DEB_EXTRACT"
    [[ -x "$DEB_EXTRACT/opt/projectx/projectx" ]] && ok ".deb contains application" || fail ".deb missing application"
    [[ -f "$DEB_EXTRACT/usr/share/applications/projectx.desktop" ]] && ok ".deb contains menu entry" || fail ".deb missing desktop file"
    [[ -f "$DEB_EXTRACT/usr/share/icons/hicolor/256x256/apps/projectx.png" ]] && ok ".deb contains icon" || fail ".deb missing icon"
    [[ -x "$DEB_EXTRACT/usr/bin/projectx" ]] && ok ".deb contains usr/bin launcher" || fail ".deb missing usr/bin/projectx"
    rm -rf "$DEB_EXTRACT"
else
    fail ".deb package not found: $DEB"
fi

WEB_COPY="${ROOT}/website/downloads/linux/$(basename "$APPIMAGE")"
[[ -f "$WEB_COPY" ]] && ok "Website download copy: $WEB_COPY" || fail "Website copy missing: $WEB_COPY"

DEB_WEB_COPY="${ROOT}/website/downloads/linux/$(basename "$DEB")"
if [[ -f "$DEB" ]]; then
    [[ -f "$DEB_WEB_COPY" ]] && ok "Website .deb copy: $DEB_WEB_COPY" || fail "Website .deb copy missing: $DEB_WEB_COPY"
fi

COMBINED_SUMS="${CHECKSUM_DIR}/SHA256SUMS"
if [[ -f "$COMBINED_SUMS" ]]; then
    ok "SHA256SUMS present: $COMBINED_SUMS"
    grep -Fq "$(basename "$APPIMAGE")" "$COMBINED_SUMS" && ok "SHA256SUMS lists AppImage" || fail "SHA256SUMS missing AppImage entry"
    if [[ -f "$DEB" ]]; then
        grep -Fq "$(basename "$DEB")" "$COMBINED_SUMS" && ok "SHA256SUMS lists .deb" || fail "SHA256SUMS missing .deb entry"
        [[ -f "${CHECKSUM_DIR}/$(basename "$DEB").sha256" ]] && ok "Per-file checksum: $(basename "$DEB").sha256" || fail "Missing checksum sidecar: $(basename "$DEB").sha256"
    fi
    [[ -f "${CHECKSUM_DIR}/$(basename "$APPIMAGE").sha256" ]] && ok "Per-file checksum: $(basename "$APPIMAGE").sha256" || fail "Missing checksum sidecar: $(basename "$APPIMAGE").sha256"
else
    fail "SHA256SUMS missing: $COMBINED_SUMS"
fi

echo ""
if [[ "$FAILED" -eq 0 ]]; then
    echo "Verification complete."
    echo "Manual: on Linux Mint, run AppImage or sudo dpkg -i .deb, confirm menu icon and First Run Wizard."
    exit 0
fi

echo "Verification failed."
exit 1
