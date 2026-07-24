#!/usr/bin/env bash
# ============================================================================
# Project X — SAVE-233 packaging verification helpers (Linux host)
# ============================================================================
# Run after: PROJECTX_BUILD=... ./scripts/build_linux_release.sh
# Does not require a system-wide dpkg install (uses extract-root tests).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OUT_DIR="${SAVE233_OUT:-/tmp}"
DEB="${ROOT}/release/linux/ProjectX.deb"
APPIMAGE="${ROOT}/release/linux/ProjectX.AppImage"
UNINSTALL_SH="${ROOT}/release/linux/ProjectX-uninstall.sh"
ISS="${ROOT}/installer/windows/projectx.iss"

pass() { echo "[PASS] $*"; }
fail() { echo "[FAIL] $*"; FAILED=1; }
FAILED=0

echo "=== SAVE-233 package size comparison ===" | tee "${OUT_DIR}/save233_sizes.log"
if [[ -f "$DEB" && -f "$APPIMAGE" ]]; then
    deb_sz="$(stat -c%s "$DEB")"
    app_sz="$(stat -c%s "$APPIMAGE")"
    {
        echo "ProjectX.deb bytes: $deb_sz ($(numfmt --to=iec --suffix=B "$deb_sz" 2>/dev/null || echo "$deb_sz"))"
        echo "ProjectX.AppImage bytes: $app_sz ($(numfmt --to=iec --suffix=B "$app_sz" 2>/dev/null || echo "$app_sz"))"
        echo "ProjectX-uninstall.sh bytes: $(stat -c%s "$UNINSTALL_SH")"
    } | tee -a "${OUT_DIR}/save233_sizes.log"
else
    fail "Linux artifacts missing under release/linux/"
fi

echo ""
echo "=== Installed file inventory (.deb extract) ===" | tee "${OUT_DIR}/save233_inventory.txt"
EXTRACT="$(mktemp -d)"
trap 'rm -rf "$EXTRACT"' EXIT
dpkg-deb -x "$DEB" "$EXTRACT"

{
    echo "build_stamp: $(tr -d '[:space:]' < "$EXTRACT/opt/projectx/resources/build_stamp" || echo MISSING)"
    echo "deb Version: $(dpkg-deb -f "$DEB" Version)"
    echo "deb Package: $(dpkg-deb -f "$DEB" Package)"
    echo ""
    echo "Key paths:"
    for p in \
        opt/projectx/projectx \
        opt/projectx/resources/build_stamp \
        opt/projectx/resources/translations/en.json \
        opt/projectx/resources/translations/hu.json \
        opt/projectx/resources/map/leaflet/leaflet.js \
        opt/projectx/resources/map/map.html \
        opt/projectx/resources/theme/colors.css \
        opt/projectx/resources/branding/projectx-logo.png \
        opt/projectx/config/playback.json \
        opt/projectx/config/camera_packs \
        opt/projectx/config/cameras \
        usr/bin/projectx \
        usr/bin/projectx-uninstall \
        usr/share/applications/projectx.desktop \
        usr/share/applications/projectx-uninstall.desktop \
        usr/share/metainfo/io.github.copex4590.projectx.appdata.xml \
        usr/share/icons/hicolor/256x256/apps/projectx.png; do
        if [[ -e "$EXTRACT/$p" ]]; then
            echo "  OK  $p"
        else
            echo "  MISS $p"
            FAILED=1
        fi
    done
    echo ""
    echo "Translation files:"
    find "$EXTRACT/opt/projectx/resources/translations" -type f -name '*.json' | sort | sed "s|^$EXTRACT/||"
    echo ""
    echo "Camera pack entries:"
    find "$EXTRACT/opt/projectx/config/camera_packs" -maxdepth 2 -type f 2>/dev/null \
        | sed "s|^$EXTRACT/||" \
        | sort \
        | head -40 || true
    echo ""
    echo "Top-level opt/projectx (sample):"
    # Avoid SIGPIPE under pipefail when head closes early.
    set +o pipefail
    ls -la "$EXTRACT/opt/projectx" | head -30
    set -o pipefail
} | tee -a "${OUT_DIR}/save233_inventory.txt"

echo ""
echo "=== Fresh / upgrade / uninstall extract tests ===" | tee "${OUT_DIR}/save233_install_tests.log"
ROOT_TEST="${OUT_DIR}/save233_dpkg_root"
rm -rf "$ROOT_TEST"
mkdir -p "$ROOT_TEST"

# Fresh install (extract)
dpkg-deb -x "$DEB" "$ROOT_TEST"
if [[ -x "$ROOT_TEST/opt/projectx/projectx" && -x "$ROOT_TEST/usr/bin/projectx" ]]; then
    pass "Fresh install extract: application + launcher present" | tee -a "${OUT_DIR}/save233_install_tests.log"
else
    fail "Fresh install extract incomplete" | tee -a "${OUT_DIR}/save233_install_tests.log"
fi

# Upgrade (re-extract over same root)
dpkg-deb -x "$DEB" "$ROOT_TEST"
if [[ -f "$ROOT_TEST/opt/projectx/resources/build_stamp" ]]; then
    pass "Upgrade extract: files replaced/retained with build_stamp" | tee -a "${OUT_DIR}/save233_install_tests.log"
else
    fail "Upgrade extract lost build_stamp" | tee -a "${OUT_DIR}/save233_install_tests.log"
fi

# Uninstall simulation (paths removed by package uninstall)
if [[ -x "$UNINSTALL_SH" ]] && grep -qE 'dpkg --purge|PACKAGE_NAME="projectx"' "$UNINSTALL_SH"; then
    pass "Uninstall script present and references dpkg purge for projectx" | tee -a "${OUT_DIR}/save233_install_tests.log"
else
    fail "Uninstall script missing/incomplete" | tee -a "${OUT_DIR}/save233_install_tests.log"
fi
if [[ -x "$ROOT_TEST/usr/bin/projectx-uninstall" ]]; then
    pass "Packaged projectx-uninstall launcher present" | tee -a "${OUT_DIR}/save233_install_tests.log"
else
    fail "Packaged projectx-uninstall missing" | tee -a "${OUT_DIR}/save233_install_tests.log"
fi
# Simulate removal of package files
rm -rf "$ROOT_TEST/opt/projectx" \
    "$ROOT_TEST/usr/bin/projectx" \
    "$ROOT_TEST/usr/bin/projectx-uninstall" \
    "$ROOT_TEST/usr/share/applications/projectx.desktop" \
    "$ROOT_TEST/usr/share/applications/projectx-uninstall.desktop" \
    "$ROOT_TEST/usr/share/metainfo" \
    "$ROOT_TEST/usr/share/icons/hicolor"
if [[ ! -e "$ROOT_TEST/opt/projectx" && ! -e "$ROOT_TEST/usr/bin/projectx" ]]; then
    pass "Uninstall simulation: package files removed" | tee -a "${OUT_DIR}/save233_install_tests.log"
else
    fail "Uninstall simulation left files behind" | tee -a "${OUT_DIR}/save233_install_tests.log"
fi

echo ""
echo "=== Windows static checklist (ISS + artifacts) ===" | tee "${OUT_DIR}/save233_win_static.log"
{
    if [[ -f "$ISS" ]]; then
        grep -E 'MyAppVersion|AppVersion|SetupIconFile|UninstallDisplay|DefaultGroupName|desktopicon|VersionInfo' "$ISS" || true
        echo "[PASS] ISS script present for static metadata review"
    else
        echo "[FAIL] Missing $ISS"
        echo fail > "${OUT_DIR}/save233_win_failed"
    fi
    if [[ -f "${ROOT}/release/windows/ProjectX-Setup.exe" ]]; then
        echo "[PASS] ProjectX-Setup.exe present"
        ls -lah "${ROOT}/release/windows/ProjectX-Setup.exe"
    else
        echo "[FAIL] ProjectX-Setup.exe missing (build on native Windows with scripts\\\\build_windows.bat)"
        echo fail > "${OUT_DIR}/save233_win_failed"
        ls -la "${ROOT}/release/windows/" || true
    fi
} | tee -a "${OUT_DIR}/save233_win_static.log"

if [[ -f "${OUT_DIR}/save233_win_failed" ]]; then
    FAILED=1
    rm -f "${OUT_DIR}/save233_win_failed"
fi

echo ""
if [[ "$FAILED" -eq 0 ]]; then
    echo "SAVE-233 helper checks complete (see ${OUT_DIR}/save233_*.log)."
    exit 0
fi
echo "SAVE-233 helper checks reported failures."
exit 1
