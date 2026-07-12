#!/usr/bin/env bash
# ============================================================================
# Project X — Linux Uninstaller
#
# Removes every path created by Project X installation so the system matches
# a machine where Project X has never been installed.
#
# Does NOT remove exported files, user-selected backups, or unrelated data.
# Does NOT remove the development source tree at ~/ProjectX unless it was
# installed via installer/linux/install.sh into ~/.local/share/projectx.
# ============================================================================

set -euo pipefail

APP_NAME="Project X"
PACKAGE_NAME="projectx"
DRY_RUN=0
ASSUME_YES=0
SELF_TEST=0
APPIMAGE_PATHS=()

usage() {
    cat <<EOF
${APP_NAME} uninstaller

Usage: $0 [options]

Options:
  --dry-run            Show what would be removed without deleting
  --yes, -y            Do not prompt for confirmation
  --appimage PATH      Also remove a ProjectX.AppImage file (repeatable)
  --self-test          Run built-in verification (uses a temporary HOME)
  -h, --help           Show this help

Examples:
  $0
  sudo $0
  $0 --appimage ~/Downloads/ProjectX.AppImage
  $0 --dry-run
EOF
}

log() {
    printf '%s\n' "$*"
}

warn() {
    printf 'Warning: %s\n' "$*" >&2
}

die() {
    printf 'Error: %s\n' "$*" >&2
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --yes|-y)
            ASSUME_YES=1
            shift
            ;;
        --self-test)
            SELF_TEST=1
            shift
            ;;
        --appimage)
            [[ $# -ge 2 ]] || die "--appimage requires a path"
            APPIMAGE_PATHS+=("$2")
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unknown option: $1"
            ;;
    esac
done

remove_path() {
    local target="$1"

    if [[ -z "$target" ]]; then
        return 0
    fi

    case "$target" in
        /|/home|/usr|/etc|"$HOME")
            die "Refusing to remove unsafe path: $target"
            ;;
    esac

    if [[ ! -e "$target" && ! -L "$target" ]]; then
        return 0
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[dry-run] remove: $target"
        return 0
    fi

    rm -rf -- "$target"
    log "Removed: $target"
}

user_home_dir() {
    local user="$1"
    getent passwd "$user" 2>/dev/null | cut -d: -f6
}

user_desktop_dir() {
    local home="$1"
    local dir=""

    if [[ -z "$home" || ! -d "$home" ]]; then
        return 0
    fi

    if [[ -f "$home/.config/user-dirs.dirs" ]]; then
        # shellcheck disable=SC1090
        . "$home/.config/user-dirs.dirs"
        eval "dir=\${XDG_DESKTOP_DIR:-}"
        if [[ -n "${dir:-}" && -d "$dir" ]]; then
            printf '%s' "$dir"
            return 0
        fi
    fi

    for candidate in "$home/Desktop" "$home/Asztal"; do
        if [[ -d "$candidate" ]]; then
            printf '%s' "$candidate"
            return 0
        fi
    done
}

collect_target_users() {
    if [[ "$SELF_TEST" -eq 1 ]]; then
        printf '%s\n' "$HOME"
        return 0
    fi

    local users=()
    local user home

    if [[ -n "${HOME:-}" && -d "$HOME" ]]; then
        users+=("$HOME")
    fi

    if [[ -n "${USER:-}" ]]; then
        home="$(user_home_dir "$USER")"
        if [[ -n "$home" ]]; then
            users+=("$home")
        fi
    fi

    if [[ -f /var/lib/projectx/install-user ]]; then
        home="$(user_home_dir "$(tr -d '[:space:]' < /var/lib/projectx/install-user)")"
        if [[ -n "$home" ]]; then
            users+=("$home")
        fi
    fi

    if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
        home="$(user_home_dir "$SUDO_USER")"
        if [[ -n "$home" ]]; then
            users+=("$home")
        fi
    fi

    printf '%s\n' "${users[@]}" | awk '!seen[$0]++'
}

stop_projectx_processes() {
    local pattern='/opt/projectx/projectx|/usr/bin/projectx|/\.local/share/projectx/bin/projectx|/dist/projectx/projectx|main\.py.*projectx'
    local pids=""
    local pid

    if command -v pgrep >/dev/null 2>&1; then
        pids="$(pgrep -f "$pattern" 2>/dev/null || true)"
    fi

    if [[ -z "$pids" ]]; then
        return 0
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[dry-run] stop processes: $pids"
        return 0
    fi

    log "Stopping Project X processes..."
    for pid in $pids; do
        [[ "$pid" -eq "$$" || "$pid" -eq "$PPID" ]] && continue
        kill "$pid" 2>/dev/null || true
    done
    sleep 1
    for pid in $pids; do
        [[ "$pid" -eq "$$" || "$pid" -eq "$PPID" ]] && continue
        kill -9 "$pid" 2>/dev/null || true
    done
}

is_projectx_desktop_file() {
    local file="$1"

    [[ -f "$file" ]] || return 1

    if grep -q '^Type=Application' "$file" 2>/dev/null &&
        grep -Eiq '^(Exec=.*projectx|Icon=projectx|StartupWMClass=ProjectX|Name=Project X)' "$file"; then
        return 0
    fi

    return 1
}

is_projectx_autostart_file() {
    local file="$1"

    [[ -f "$file" ]] || return 1
    grep -Eiq 'projectx|/opt/projectx|Project X' "$file"
}

remove_user_desktop_entries() {
    local home="$1"
    local desktop_dir file

    remove_path "$home/.local/share/applications/projectx.desktop"
    remove_path "$home/.local/bin/projectx"

    desktop_dir="$(user_desktop_dir "$home")"
    if [[ -n "$desktop_dir" ]]; then
        remove_path "$desktop_dir/Project X.desktop"
    fi

    remove_path "$home/Desktop/Project X.desktop"
    remove_path "$home/Asztal/Project X.desktop"

    for file in "$home/.local/share/applications/"*.desktop; do
        [[ -e "$file" ]] || continue
        if is_projectx_desktop_file "$file"; then
            remove_path "$file"
        fi
    done

    if [[ -d "$home/.config/autostart" ]]; then
        for file in "$home/.config/autostart/"*.desktop; do
            [[ -e "$file" ]] || continue
            if is_projectx_autostart_file "$file"; then
                remove_path "$file"
            fi
        done
    fi
}

remove_user_icons() {
    local home="$1"
    local icon_root="$home/.local/share/icons/hicolor"
    local size_dir

    if [[ ! -d "$icon_root" ]]; then
        return 0
    fi

    for size_dir in "$icon_root"/*/apps/projectx.png; do
        [[ -e "$size_dir" ]] || continue
        remove_path "$size_dir"
    done
}

remove_user_state() {
    local home="$1"

    remove_user_desktop_entries "$home"
    remove_user_icons "$home"
    remove_path "$home/.local/share/projectx"
    remove_path "$home/.local/share/Project X"
    remove_path "$home/.cache/Project X"
}

remove_system_icons() {
    local size
    for size in 16 22 24 32 48 64 128 256 512; do
        remove_path "/usr/share/icons/hicolor/${size}x${size}/apps/projectx.png"
    done
}

remove_system_artifacts() {
    remove_path "/opt/projectx"
    remove_path "/usr/bin/projectx"
    remove_path "/usr/bin/projectx-uninstall"
    remove_path "/usr/share/applications/projectx.desktop"
    remove_path "/usr/share/metainfo/io.github.copex4590.projectx.appdata.xml"
    remove_system_icons
    remove_path "/var/lib/projectx"
}

deb_package_installed() {
    dpkg-query -W -f='${Status}' "$PACKAGE_NAME" 2>/dev/null | grep -q 'ok installed'
}

deb_package_present() {
    dpkg-query -W -f='${Status}' "$PACKAGE_NAME" 2>/dev/null | grep -Eq 'ok installed|ok config-files'
}

remove_deb_package() {
    if ! deb_package_present; then
        return 0
    fi

    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[dry-run] dpkg --purge $PACKAGE_NAME"
        return 0
    fi

    if [[ "$EUID" -ne 0 ]]; then
        die "Removing the ${PACKAGE_NAME} package requires root. Re-run with sudo."
    fi

    log "Removing Debian package: ${PACKAGE_NAME}"
    dpkg --purge "$PACKAGE_NAME"
}

refresh_desktop_integration() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[dry-run] refresh desktop database and icon cache"
        return 0
    fi

    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database /usr/share/applications 2>/dev/null || true
        if [[ -d "$HOME/.local/share/applications" ]]; then
            update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
        fi
    fi

    if command -v gtk-update-icon-cache >/dev/null 2>&1 &&
        [[ -d /usr/share/icons/hicolor ]]; then
        gtk-update-icon-cache -f /usr/share/icons/hicolor 2>/dev/null || true
    fi
}

discover_appimages() {
    local home="$1"
    local dir candidate

    for dir in \
        "${XDG_DOWNLOAD_DIR:-}" \
        "$home/Downloads" \
        "$home/Letöltések" \
        "$home/Desktop" \
        "$home/Asztal"; do
        [[ -n "$dir" && -d "$dir" ]] || continue
        for candidate in "$dir"/ProjectX.AppImage "$dir"/ProjectX-*.AppImage; do
            [[ -f "$candidate" ]] || continue
            APPIMAGE_PATHS+=("$candidate")
        done
    done

    if [[ "${#APPIMAGE_PATHS[@]}" -eq 0 ]]; then
        return 0
    fi

    local deduped=()
    local path
    while IFS= read -r path; do
        deduped+=("$path")
    done < <(printf '%s\n' "${APPIMAGE_PATHS[@]}" | awk '!seen[$0]++')
    APPIMAGE_PATHS=("${deduped[@]}")
}

remove_appimages() {
    local path
    for path in "${APPIMAGE_PATHS[@]}"; do
        remove_path "$path"
    done
}

confirm_uninstall() {
    if [[ "$ASSUME_YES" -eq 1 || "$DRY_RUN" -eq 1 || "$SELF_TEST" -eq 1 ]]; then
        return 0
    fi

    log "This will completely remove ${APP_NAME} and all of its local data."
    log "Exported files and unrelated backups will not be touched."
    printf 'Continue? [y/N] '
    local reply
    read -r reply
    case "$reply" in
        y|Y|yes|YES)
            ;;
        *)
            log "Uninstall cancelled."
            exit 0
            ;;
    esac
}

run_uninstall() {
    local home

    stop_projectx_processes
    discover_appimages "$HOME"

    while IFS= read -r home; do
        [[ -n "$home" ]] || continue
        log "Removing user data for: $home"
        remove_user_state "$home"
    done < <(collect_target_users)

    if deb_package_installed; then
        remove_deb_package
    fi

    if [[ "$EUID" -eq 0 ]]; then
        remove_system_artifacts
    elif [[ -d /opt/projectx || -x /usr/bin/projectx ]]; then
        warn "System files remain under /opt/projectx or /usr/bin/projectx."
        warn "Re-run with sudo to remove the installed package and system files."
    fi

    remove_appimages
    refresh_desktop_integration
}

run_self_test() {
    local test_home
    test_home="$(mktemp -d "${TMPDIR:-/tmp}/projectx-uninstall-test.XXXXXX")"

    log "Running self-test in $test_home"

    HOME="$test_home"
    export HOME

    mkdir -p \
        "$HOME/.local/share/projectx/config" \
        "$HOME/.local/share/projectx/data/Hajók" \
        "$HOME/.local/share/Project X/logs" \
        "$HOME/.cache/Project X/Project X" \
        "$HOME/.local/bin" \
        "$HOME/.local/share/applications" \
        "$HOME/.local/share/icons/hicolor/256x256/apps" \
        "$HOME/.config/autostart" \
        "$HOME/Desktop" \
        "$HOME/Downloads" \
        "$HOME/unrelated-backup"

    ln -s "$HOME/.local/share/projectx/bin/projectx" "$HOME/.local/bin/projectx" 2>/dev/null || true
    printf '%s\n' '{"language":"en"}' > "$HOME/.local/share/projectx/config/preferences.json"
    printf '%s\n' '[]' > "$HOME/.local/share/projectx/config/observation_points.json"
    printf '%s\n' 'log' > "$HOME/.local/share/Project X/logs/projectx.log"
    printf '%s\n' 'cache' > "$HOME/.cache/Project X/Project X/cache.bin"
    cp /dev/null "$HOME/.local/share/icons/hicolor/256x256/apps/projectx.png"
    cat > "$HOME/.local/share/applications/projectx.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Project X
Exec=/opt/projectx/projectx
Icon=projectx
StartupWMClass=ProjectX
EOF
    cp "$HOME/.local/share/applications/projectx.desktop" "$HOME/Desktop/Project X.desktop"
    cat > "$HOME/.config/autostart/projectx.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Exec=/usr/bin/projectx
EOF
    cat > "$HOME/.config/autostart/unrelated.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Exec=/usr/bin/true
Name=Keep Me
EOF
    printf '%s\n' 'backup' > "$HOME/unrelated-backup/export.csv"
    touch "$HOME/Downloads/ProjectX.AppImage"
    APPIMAGE_PATHS=("$HOME/Downloads/ProjectX.AppImage")

    DRY_RUN=0
    ASSUME_YES=1
    run_uninstall

    local artifact
    local artifacts=(
        "$HOME/.local/share/projectx"
        "$HOME/.local/share/Project X"
        "$HOME/.cache/Project X"
        "$HOME/.local/bin/projectx"
        "$HOME/.local/share/applications/projectx.desktop"
        "$HOME/Desktop/Project X.desktop"
        "$HOME/.config/autostart/projectx.desktop"
        "$HOME/.local/share/icons/hicolor/256x256/apps/projectx.png"
        "$HOME/Downloads/ProjectX.AppImage"
    )

    for artifact in "${artifacts[@]}"; do
        if [[ -e "$artifact" || -L "$artifact" ]]; then
            printf 'Self-test FAILED. Remaining artifact: %s\n' "$artifact" >&2
            rm -rf "$test_home"
            exit 1
        fi
    done

    if [[ ! -f "$HOME/.config/autostart/unrelated.desktop" ]]; then
        printf 'Self-test FAILED. Unrelated autostart entry was removed.\n' >&2
        rm -rf "$test_home"
        exit 1
    fi

    if [[ ! -f "$HOME/unrelated-backup/export.csv" ]]; then
        printf 'Self-test FAILED. Unrelated backup was removed.\n' >&2
        rm -rf "$test_home"
        exit 1
    fi

    rm -rf "$test_home"
    log "Self-test PASS"
}

main() {
    if [[ "$SELF_TEST" -eq 1 ]]; then
        run_self_test
        exit 0
    fi

    confirm_uninstall
    run_uninstall
    log "${APP_NAME} uninstall complete."
}

main "$@"
