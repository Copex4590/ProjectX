#!/usr/bin/env bash
# ============================================================================
# Project X — Linux release package build (SAVE-077)
# ============================================================================
#
# Produces:
#   release/linux/ProjectX-<version>-x86_64.AppImage   (primary)
#   release/linux/projectx_<version>_amd64.deb         (secondary)
#   website/downloads/linux/                             (website copy)
#
# Requires: python3, curl, mksquashfs (squashfs-tools), dpkg-deb (optional)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHON="${PROJECTX_PYTHON:-}"
SKIP_DEB="${SKIP_DEB:-0}"
PREPARE_ONLY=0
APPIMAGE_NAME=""
DEB_NAME=""
RELEASE_DIR="${ROOT}/release/linux"
WEB_DOWNLOAD_DIR="${ROOT}/website/downloads/linux"
APPDIR="${ROOT}/build/appimage/AppDir"
CACHE_DIR="${ROOT}/.cache"
APPIMAGETOOL="${CACHE_DIR}/appimagetool-x86_64.AppImage"
VERSION=""

usage() {
    cat <<EOF
Project X Linux release build

Usage: $0 [options]

Options:
  --prepare-only   Verify assets and paths only
  -h, --help       Show this help

Environment:
  PROJECTX_PYTHON   Python for build (default: .venv/bin/python)
  SKIP_DEB=1        Skip .deb generation
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prepare-only)
            PREPARE_ONLY=1
            shift
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 1
            ;;
    esac
done

require_command() {
    if ! command -v "$1" >/dev/null 2>&1; then
        echo "[FAIL] Missing required command: $1" >&2
        exit 1
    fi
}

read_version() {
    VERSION="$("$PYTHON" - <<'PY'
from pathlib import Path
import sys
sys.path.insert(0, str(Path("src").resolve()))
from version import PROJECT_VERSION
print(PROJECT_VERSION)
PY
)"
    APPIMAGE_NAME="ProjectX-${VERSION}-x86_64.AppImage"
    DEB_NAME="projectx_${VERSION}_amd64.deb"
}

ensure_build_python() {
    if [[ -n "${PROJECTX_PYTHON:-}" ]]; then
        PYTHON="$PROJECTX_PYTHON"
        return
    fi
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        PYTHON="$ROOT/.venv/bin/python"
        return
    fi
    require_command python3
    echo "Creating build virtual environment at ${ROOT}/.venv ..."
    python3 -m venv "$ROOT/.venv"
    PYTHON="$ROOT/.venv/bin/python"
}

prepare_assets() {
    if [[ ! -f "$ROOT/src/resources/map/leaflet/leaflet.js" ]]; then
        echo "Fetching Leaflet assets..."
        require_command curl
        bash "$ROOT/scripts/fetch_leaflet.sh"
    fi
    for asset in projectx-logo.png projectx.ico; do
        if [[ ! -f "$ROOT/src/resources/branding/$asset" ]]; then
            echo "Generating branding assets..."
            "$PYTHON" "$ROOT/scripts/generate_branding_assets.py"
            break
        fi
    done
}

verify_runtime_resources() {
    echo "Verifying runtime resources in source tree..."
    "$PYTHON" - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path("src").resolve()))
from app import paths

required = [
    paths.resource_path("translations", "en.json"),
    paths.resource_path("translations", "hu.json"),
    paths.resource_path("map", "leaflet", "leaflet.js"),
    paths.resource_path("map", "map.html"),
    paths.resource_path("branding", "projectx-logo.png"),
    paths.resource_path("branding", "projectx.ico"),
    paths.bundle_dir() / "config" / "playback.json",
]
missing = [str(p) for p in required if not p.exists()]
if missing:
    raise SystemExit("Missing resources:\n  " + "\n  ".join(missing))
print("Runtime resources verified.")
PY
}

clean_release_builds() {
    echo "Cleaning previous build artifacts..."
    bash "$ROOT/scripts/clean_build.sh"
    rm -rf "$ROOT/build/appimage"
    rm -rf "$RELEASE_DIR"/*
    mkdir -p "$RELEASE_DIR" "$WEB_DOWNLOAD_DIR" "$CACHE_DIR"
}

install_build_deps() {
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install -r "$ROOT/requirements.txt" pyinstaller
}

run_pyinstaller() {
    echo "Running PyInstaller..."
    "$PYTHON" -m PyInstaller --noconfirm "$ROOT/installer/projectx.spec"
    if [[ ! -x "$ROOT/dist/projectx/projectx" ]]; then
        echo "[FAIL] PyInstaller output missing: dist/projectx/projectx" >&2
        exit 1
    fi
    echo "[OK] PyInstaller bundle: dist/projectx/"
}

verify_bundle_contents() {
    local bundle="$ROOT/dist/projectx"
    echo "Verifying PyInstaller bundle contents..."
    local required=(
        "$bundle/projectx"
        "$bundle/resources/translations/en.json"
        "$bundle/resources/translations/hu.json"
        "$bundle/resources/map/leaflet/leaflet.js"
        "$bundle/resources/branding/projectx-logo.png"
        "$bundle/projectx.ico"
        "$bundle/config/playback.json"
    )
    local path
    for path in "${required[@]}"; do
        if [[ ! -e "$path" ]]; then
            echo "[FAIL] Missing in bundle: $path" >&2
            exit 1
        fi
    done
    if [[ ! -x "$bundle/projectx" ]]; then
        echo "[FAIL] Main executable is not executable: $bundle/projectx" >&2
        exit 1
    fi
    echo "[OK] Bundle contains application, icons, resources, translations, branding, config."
}

create_appdir() {
    echo "Creating AppImage AppDir..."
    rm -rf "$APPDIR"
    mkdir -p "$APPDIR/usr/lib/projectx"

    cp -a "$ROOT/dist/projectx/." "$APPDIR/usr/lib/projectx/"
    cp "$ROOT/installer/linux/projectx-appimage.desktop" "$APPDIR/projectx.desktop"
    cp "$ROOT/src/resources/branding/projectx-logo.png" "$APPDIR/projectx.png"

    cat > "$APPDIR/AppRun" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(dirname "$(readlink -f "${0}")")"
exec "${HERE}/usr/lib/projectx/projectx" "$@"
EOF
    chmod +x "$APPDIR/AppRun" "$APPDIR/usr/lib/projectx/projectx"
    echo "[OK] AppDir prepared with AppRun, desktop file, and icon."
}

ensure_appimagetool() {
    if [[ -x "$APPIMAGETOOL" ]]; then
        return
    fi
    require_command curl
    echo "Downloading appimagetool..."
    curl -fsSL \
        -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    chmod +x "$APPIMAGETOOL"
}

build_appimage() {
    require_command mksquashfs
    ensure_appimagetool
    local output="${RELEASE_DIR}/${APPIMAGE_NAME}"
    echo "Building AppImage: ${APPIMAGE_NAME}"
    ARCH=x86_64 "$APPIMAGETOOL" "$APPDIR" "$output"
    chmod +x "$output"
    cp -f "$output" "${WEB_DOWNLOAD_DIR}/${APPIMAGE_NAME}"
    echo "[OK] AppImage: $output"
}

build_deb() {
    if [[ "$SKIP_DEB" == "1" ]]; then
        echo "[SKIP] .deb package (SKIP_DEB=1)."
        return
    fi
    if ! command -v dpkg-deb >/dev/null 2>&1; then
        echo "[SKIP] .deb package (dpkg-deb not found)."
        return
    fi

    local staging="$ROOT/build/deb/projectx_${VERSION}_amd64"
    local output="${RELEASE_DIR}/${DEB_NAME}"
    rm -rf "$staging"
    mkdir -p "$staging/DEBIAN"
    mkdir -p "$staging/opt/projectx"
    mkdir -p "$staging/usr/bin"
    mkdir -p "$staging/usr/share/applications"
    mkdir -p "$staging/usr/share/icons/hicolor/256x256/apps"

    cp -a "$ROOT/dist/projectx/." "$staging/opt/projectx/"
    chmod +x "$staging/opt/projectx/projectx"

    cat > "$staging/usr/bin/projectx" <<'EOF'
#!/bin/sh
exec /opt/projectx/projectx "$@"
EOF
    chmod +x "$staging/usr/bin/projectx"

    cp "$ROOT/installer/linux/projectx-deb.desktop" "$staging/usr/share/applications/projectx.desktop"
    cp "$ROOT/src/resources/branding/projectx-logo.png" \
        "$staging/usr/share/icons/hicolor/256x256/apps/projectx.png"

    cat > "$staging/DEBIAN/control" <<EOF
Package: projectx
Version: ${VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Project X <https://github.com/Copex4590/ProjectX>
Depends: libgl1, libglib2.0-0, libxkbcommon0, libxcb-xinerama0, libegl1, libnss3
Description: Project X — Danube vessel monitoring platform
 Desktop application for AIS monitoring, maps, cameras, timeline, and alerts.
EOF

    cat > "$staging/DEBIAN/postinst" <<'EOF'
#!/bin/sh
set -e
chmod +x /opt/projectx/projectx /usr/bin/projectx 2>/dev/null || true
if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database /usr/share/applications 2>/dev/null || true
fi
if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true
fi
exit 0
EOF
    chmod 755 "$staging/DEBIAN/postinst"

    dpkg-deb --build --root-owner-group "$staging" "$output"
    cp -f "$output" "${WEB_DOWNLOAD_DIR}/${DEB_NAME}"
    echo "[OK] Debian package: $output"
}

write_checksums() {
    bash "$ROOT/scripts/generate_release_checksums.sh"
}

verify_release_packages() {
    echo "Verifying release packages..."
    local appimage="${RELEASE_DIR}/${APPIMAGE_NAME}"
    if [[ ! -x "$appimage" ]]; then
        echo "[FAIL] AppImage missing or not executable: $appimage" >&2
        exit 1
    fi

    local extract_dir
    extract_dir="$(mktemp -d)"
    cd "$extract_dir"
    "$appimage" --appimage-extract >/dev/null
    local required=(
        "squashfs-root/AppRun"
        "squashfs-root/projectx.desktop"
        "squashfs-root/projectx.png"
        "squashfs-root/usr/lib/projectx/projectx"
        "squashfs-root/usr/lib/projectx/resources/translations/en.json"
        "squashfs-root/usr/lib/projectx/resources/branding/projectx-logo.png"
    )
    local path
    for path in "${required[@]}"; do
        if [[ ! -e "$path" ]]; then
            echo "[FAIL] AppImage missing: $path" >&2
            rm -rf "$extract_dir"
            exit 1
        fi
    done
    if [[ ! -x "squashfs-root/AppRun" ]] || [[ ! -x "squashfs-root/usr/lib/projectx/projectx" ]]; then
        echo "[FAIL] AppImage executables lack execute permission." >&2
        rm -rf "$extract_dir"
        exit 1
    fi
    rm -rf "$extract_dir"
    echo "[OK] AppImage contents verified (app, icon, desktop, resources, translations, branding)."

    if [[ -f "${RELEASE_DIR}/${DEB_NAME}" ]]; then
        local deb_extract
        deb_extract="$(mktemp -d)"
        dpkg-deb -x "${RELEASE_DIR}/${DEB_NAME}" "$deb_extract"
        [[ -x "$deb_extract/opt/projectx/projectx" ]] || {
            echo "[FAIL] .deb missing application binary." >&2
            rm -rf "$deb_extract"
            exit 1
        }
        [[ -f "$deb_extract/usr/share/applications/projectx.desktop" ]] || {
            echo "[FAIL] .deb missing desktop file." >&2
            rm -rf "$deb_extract"
            exit 1
        }
        [[ -f "$deb_extract/usr/share/icons/hicolor/256x256/apps/projectx.png" ]] || {
            echo "[FAIL] .deb missing icon." >&2
            rm -rf "$deb_extract"
            exit 1
        }
        [[ -x "$deb_extract/usr/bin/projectx" ]] || {
            echo "[FAIL] .deb missing usr/bin launcher." >&2
            rm -rf "$deb_extract"
            exit 1
        }
        rm -rf "$deb_extract"
        echo "[OK] .deb contents verified (menu entry, icon, application)."
    fi
}

print_summary() {
    echo ""
    echo "============================================================"
    echo "LINUX RELEASE BUILD SUCCESSFUL"
    echo "============================================================"
    echo "Version: ${VERSION}"
    echo "Output directory: ${RELEASE_DIR}"
    ls -lh "$RELEASE_DIR" 2>/dev/null || true
    echo ""
    echo "Website copies: ${WEB_DOWNLOAD_DIR}"
    echo "Next: ./scripts/verify_linux_release.sh"
    echo "Docs: docs/LINUX_INSTALLER.md"
    echo ""
}

PREPARE_ONLY="${PREPARE_ONLY:-0}"

if [[ -z "$PYTHON" ]]; then
    if [[ -x "$ROOT/.venv/bin/python" ]]; then
        PYTHON="$ROOT/.venv/bin/python"
    else
        PYTHON="python3"
    fi
fi

require_command curl
read_version

prepare_assets
verify_runtime_resources

if [[ "$PREPARE_ONLY" == "1" ]]; then
    echo "Prepare-only complete."
    exit 0
fi

clean_release_builds
ensure_build_python
install_build_deps
run_pyinstaller
verify_bundle_contents
create_appdir
build_appimage
build_deb
write_checksums
verify_release_packages
print_summary
