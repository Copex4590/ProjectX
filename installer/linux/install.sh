#!/usr/bin/env bash
# ============================================================================
# Project X — Linux Installer
# ============================================================================

set -euo pipefail

APP_NAME="Project X"
INSTALL_DIR="${HOME}/.local/share/projectx"
BIN_DIR="${HOME}/.local/bin"
DESKTOP_DIR="${HOME}/.local/share/applications"
ICON_DIR="${HOME}/.local/share/icons/hicolor/256x256/apps"
DESKTOP_SHORTCUT=1
START_MENU_SHORTCUT=1
LAUNCH_AFTER_INSTALL=0
INSTALL_ICON=1
SOURCE_DIR=""

usage() {
    cat <<EOF
${APP_NAME} installer

Usage: $0 [options]

Options:
  --prefix DIR           Install directory (default: ~/.local/share/projectx)
  --source DIR           Source tree (default: repository root)
  --no-desktop           Skip desktop shortcut
  --no-start-menu        Skip Start Menu / applications menu entry
  --no-icon              Skip system icon theme installation
  --launch               Launch Project X after installation
  -h, --help             Show this help
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --prefix)
            INSTALL_DIR="$2"
            shift 2
            ;;
        --source)
            SOURCE_DIR="$2"
            shift 2
            ;;
        --no-desktop)
            DESKTOP_SHORTCUT=0
            shift
            ;;
        --no-start-menu)
            START_MENU_SHORTCUT=0
            shift
            ;;
        --no-icon)
            INSTALL_ICON=0
            shift
            ;;
        --launch)
            LAUNCH_AFTER_INSTALL=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SOURCE_DIR="${SOURCE_DIR:-${ROOT_DIR}}"

mkdir -p "${INSTALL_DIR}" "${INSTALL_DIR}/bin" "${BIN_DIR}" "${DESKTOP_DIR}" "${ICON_DIR}"

echo "Installing ${APP_NAME} to ${INSTALL_DIR}"

cp -a "${SOURCE_DIR}/src" "${INSTALL_DIR}/"
cp -a "${SOURCE_DIR}/requirements.txt" "${INSTALL_DIR}/"

if [[ -d "${SOURCE_DIR}/data" ]]; then
    cp -a "${SOURCE_DIR}/data" "${INSTALL_DIR}/"
else
    mkdir -p "${INSTALL_DIR}/data"
fi

ICON_SRC="${SOURCE_DIR}/src/resources/branding/projectx-logo.png"
ICON_TARGET="${INSTALL_DIR}/projectx.png"

if [[ -f "${ICON_SRC}" ]]; then
    cp "${ICON_SRC}" "${ICON_TARGET}"
fi

if [[ "${INSTALL_ICON}" -eq 1 && -f "${ICON_TARGET}" ]]; then
    mkdir -p "${ICON_DIR}"
    cp "${ICON_TARGET}" "${ICON_DIR}/projectx.png" 2>/dev/null || INSTALL_ICON=0
fi

DESKTOP_ICON="${ICON_TARGET}"
if [[ "${INSTALL_ICON}" -eq 1 ]]; then
    DESKTOP_ICON="projectx"
fi

cat > "${INSTALL_DIR}/bin/projectx" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "${INSTALL_DIR}/src"
exec python3 main.py "\$@"
EOF
chmod +x "${INSTALL_DIR}/bin/projectx"
ln -sf "${INSTALL_DIR}/bin/projectx" "${BIN_DIR}/projectx" 2>/dev/null || true

if [[ "${START_MENU_SHORTCUT}" -eq 1 ]]; then
    sed -e "s|@INSTALL_DIR@|${INSTALL_DIR}|g" \
        -e "s|Icon=projectx|Icon=${DESKTOP_ICON}|g" \
        "${SCRIPT_DIR}/projectx.desktop" > "${DESKTOP_DIR}/projectx.desktop"
    chmod +x "${DESKTOP_DIR}/projectx.desktop"
    echo "Applications menu shortcut created."
fi

if [[ "${DESKTOP_SHORTCUT}" -eq 1 ]]; then
    DESKTOP_PATH="${HOME}/Desktop"
    XDG_DESKTOP="${XDG_DESKTOP_DIR:-${DESKTOP_PATH}}"

    if [[ -d "${XDG_DESKTOP}" ]]; then
        cp "${DESKTOP_DIR}/projectx.desktop" "${XDG_DESKTOP}/Project X.desktop"
        chmod +x "${XDG_DESKTOP}/Project X.desktop"
        echo "Desktop shortcut created."
    fi
fi

echo "${APP_NAME} installed successfully."

if [[ "${LAUNCH_AFTER_INSTALL}" -eq 1 ]]; then
    echo "Launching ${APP_NAME}..."
    nohup "${INSTALL_DIR}/bin/projectx" >/dev/null 2>&1 &
fi
