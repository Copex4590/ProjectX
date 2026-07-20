#!/usr/bin/env bash
# ============================================================================
# Project X — Verify Linux release packages (SAVE-077 / SAVE-085)
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

RELEASE_DIR="${ROOT}/release/linux"
APPIMAGE="${RELEASE_DIR}/ProjectX.AppImage"
DEB="${RELEASE_DIR}/ProjectX.deb"
SUMS="${RELEASE_DIR}/SHA256SUMS"
FAILED=0

fail() {
    echo "[FAIL] $*"
    FAILED=1
}

ok() {
    echo "[OK] $*"
}

echo "Verifying Linux public release under ${RELEASE_DIR}..."

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
    squashfs-root/usr/lib/projectx/resources/map/cesium/Cesium.js \
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

if grep -q '^Name=Project X' squashfs-root/projectx.desktop; then
    ok "Desktop menu name is Project X"
else
    fail "Desktop file Name is not 'Project X'"
fi

if grep -q '^Comment=Professional Maritime Monitoring Platform' squashfs-root/projectx.desktop; then
    ok "Desktop short description configured"
else
    fail "Desktop file Comment missing expected short description"
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
    [[ -x "$DEB_EXTRACT/usr/bin/projectx" ]] && ok ".deb contains usr/bin launcher" || fail ".deb missing usr/bin/projectx"
    [[ -x "$DEB_EXTRACT/usr/bin/projectx-uninstall" ]] && ok ".deb contains projectx-uninstall" || fail ".deb missing usr/bin/projectx-uninstall"
    [[ -f "$DEB_EXTRACT/usr/share/applications/projectx-uninstall.desktop" ]] && ok ".deb contains uninstall menu entry" || fail ".deb missing uninstall desktop entry"
    [[ -f "$DEB_EXTRACT/usr/share/metainfo/io.github.copex4590.projectx.appdata.xml" ]] && ok ".deb contains AppStream metadata" || fail ".deb missing AppStream metadata"

    if grep -q '^Name=Project X' "$DEB_EXTRACT/usr/share/applications/projectx.desktop"; then
        ok ".deb menu entry displays Project X"
    else
        fail ".deb desktop Name is not 'Project X'"
    fi

    if grep -q '^Comment=Professional Maritime Monitoring Platform' "$DEB_EXTRACT/usr/share/applications/projectx.desktop"; then
        ok ".deb short description configured"
    else
        fail ".deb desktop Comment missing expected short description"
    fi

    if grep -q '^Name=Project X Uninstall' "$DEB_EXTRACT/usr/share/applications/projectx-uninstall.desktop"; then
        ok ".deb uninstall menu entry displays Project X Uninstall"
    else
        fail ".deb uninstall desktop Name is not 'Project X Uninstall'"
    fi

    uninstall_exec="$(grep -E '^Exec=' "$DEB_EXTRACT/usr/share/applications/projectx-uninstall.desktop" | head -n1 | cut -d= -f2-)"
    if [[ "$uninstall_exec" == "/usr/bin/projectx-uninstall" ]]; then
        ok ".deb uninstall desktop Exec=/usr/bin/projectx-uninstall"
    else
        fail ".deb uninstall desktop Exec is not /usr/bin/projectx-uninstall (got: ${uninstall_exec:-<empty>})"
    fi

    if [[ -x "$DEB_EXTRACT/usr/bin/projectx-uninstall" ]]; then
        ok ".deb uninstall launcher target is executable"
    else
        fail ".deb uninstall launcher target is missing or not executable"
    fi

    if grep -q 'remove_cached_configured_data_roots' "$DEB_EXTRACT/usr/bin/projectx-uninstall"; then
        ok ".deb uninstaller removes configured data_directory"
    else
        fail ".deb uninstaller missing configured data_directory removal"
    fi

    for icon_size in 16 22 24 32 48 64 128 256 512; do
        icon_path="$DEB_EXTRACT/usr/share/icons/hicolor/${icon_size}x${icon_size}/apps/projectx.png"
        if [[ -f "$icon_path" ]]; then
            ok ".deb icon installed: ${icon_size}x${icon_size}"
        else
            fail ".deb missing icon size: ${icon_size}x${icon_size}"
        fi
    done

    if grep -q '<name>Project X</name>' "$DEB_EXTRACT/usr/share/metainfo/io.github.copex4590.projectx.appdata.xml"; then
        ok "AppStream title is Project X"
    else
        fail "AppStream metadata missing Project X title"
    fi

    if grep -q 'Professional Maritime Monitoring Platform' "$DEB_EXTRACT/usr/share/metainfo/io.github.copex4590.projectx.appdata.xml"; then
        ok "AppStream summary configured"
    else
        fail "AppStream metadata missing expected summary"
    fi

    CONTROL="$(dpkg-deb -f "$DEB" Description)"
    if echo "$CONTROL" | head -n1 | grep -q '^Project X$'; then
        ok "Package title for software managers: Project X"
    else
        fail "Package Description first line is not 'Project X'"
    fi

    if echo "$CONTROL" | grep -q 'Professional Maritime Monitoring Platform'; then
        ok "Package description includes user-oriented summary"
    else
        fail "Package Description missing user-oriented summary"
    fi

    PKG_NAME="$(dpkg-deb -f "$DEB" Package)"
    if [[ "$PKG_NAME" == "projectx" ]]; then
        ok "Uninstall package name: projectx (sudo dpkg -r projectx)"
    else
        fail "Unexpected package name for uninstall: $PKG_NAME"
    fi

    rm -rf "$DEB_EXTRACT"
else
    fail ".deb package not found: $DEB"
fi

WEB_APPIMAGE="${ROOT}/website/downloads/linux/ProjectX.AppImage"
[[ -f "$WEB_APPIMAGE" ]] && ok "Website AppImage copy present" || fail "Website copy missing: $WEB_APPIMAGE"

WEB_DEB="${ROOT}/website/downloads/linux/ProjectX.deb"
[[ -f "$WEB_DEB" ]] && ok "Website .deb copy present" || fail "Website copy missing: $WEB_DEB"

WEB_SUMS="${ROOT}/website/downloads/linux/SHA256SUMS"
[[ -f "$WEB_SUMS" ]] && ok "Website SHA256SUMS copy present" || fail "Website copy missing: $WEB_SUMS"

if [[ -f "$SUMS" ]]; then
    ok "SHA256SUMS present: ${SUMS#${ROOT}/}"
    grep -Fq "ProjectX.AppImage" "$SUMS" && ok "SHA256SUMS lists AppImage" || fail "SHA256SUMS missing AppImage entry"
    grep -Fq "ProjectX.deb" "$SUMS" && ok "SHA256SUMS lists .deb" || fail "SHA256SUMS missing .deb entry"

    while IFS= read -r base; do
        [[ -n "$base" ]] || continue
        artifact="${RELEASE_DIR}/${base}"
        [[ -f "$artifact" ]] || continue
        expected="$(grep -F "  ${base}" "$SUMS" | awk '{print $1}' | head -n1)"
        actual="$(sha256sum "$artifact" | awk '{print $1}')"
        if [[ "$expected" == "$actual" ]]; then
            ok "Checksum matches: $base"
        else
            fail "Checksum mismatch: $base"
        fi
    done < <(grep -F '  ' "$SUMS" | awk '{print $NF}')
else
    fail "SHA256SUMS missing: $SUMS"
fi

echo ""
if [[ "$FAILED" -eq 0 ]]; then
    echo "Verification complete."
    echo "Manual: on Linux Mint, run AppImage or sudo dpkg -i ProjectX.deb, confirm menu icon and First Run Wizard."
    exit 0
fi

echo "Verification failed."
exit 1
