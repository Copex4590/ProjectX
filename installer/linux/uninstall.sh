#!/usr/bin/env bash
# ============================================================================
# Project X — Linux Uninstaller
# ============================================================================

set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/projectx"
BIN_LINK="${HOME}/.local/bin/projectx"
DESKTOP_FILE="${HOME}/.local/share/applications/projectx.desktop"
ICON_FILE="${HOME}/.local/share/icons/hicolor/256x256/apps/projectx.png"
DESKTOP_SHORTCUT="${HOME}/Desktop/Project X.desktop"
XDG_DESKTOP="${XDG_DESKTOP_DIR:-${HOME}/Desktop}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            INSTALL_DIR="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

rm -f "${BIN_LINK}" "${DESKTOP_FILE}" "${ICON_FILE}"
rm -f "${DESKTOP_SHORTCUT}" "${XDG_DESKTOP}/Project X.desktop"
rm -rf "${INSTALL_DIR}"

echo "Project X uninstalled."
