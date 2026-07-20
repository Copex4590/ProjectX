#!/usr/bin/env bash
# ============================================================================
# Project X — Linux Uninstaller
#
# Removes every path created by Project X installation so the system matches
# a machine where Project X has never been installed.
#
# Does NOT remove exported files, user-selected backups, or unrelated data.
# When the user chooses to remove Project X user data, the configured data root
# referenced by preferences.json is removed in addition to bootstrap/cache paths.
# Does NOT remove the development source tree at ~/ProjectX unless it was
# installed via installer/linux/install.sh into ~/.local/share/projectx.
# ============================================================================

set -euo pipefail

APP_NAME="Project X"
PACKAGE_NAME="projectx"
DRY_RUN=0
ASSUME_YES=0
SELF_TEST=0
PRIVILEGED_ONLY=0
REMOVE_USER_DATA=1
APPIMAGE_PATHS=()
CONFIGURED_DATA_ROOTS=()
SCRIPT_PATH="$(readlink -f "$0" 2>/dev/null || printf '%s' "$0")"

usage() {
    cat <<EOF
${APP_NAME} uninstaller

Usage: $0 [options]

Options:
  --dry-run            Show what would be removed without deleting
  --yes, -y            Do not prompt for confirmation
  --privileged-only    Internal: run package/system removal as root
  --appimage PATH      Also remove a ProjectX.AppImage file (repeatable)
  --self-test          Run built-in verification (uses a temporary HOME)
  -h, --help           Show this help

Examples:
  $0
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
        --privileged-only)
            PRIVILEGED_ONLY=1
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

expand_user_path() {
    local home="$1"
    local target="$2"

    if [[ -z "$target" ]]; then
        return 0
    fi

    if [[ "$target" == "~" ]]; then
        printf '%s' "$home"
        return 0
    fi

    if [[ "${target:0:2}" == "~/" ]]; then
        printf '%s' "$home/${target:2}"
        return 0
    fi

    if [[ "${target:0:6}" == '$HOME/' ]]; then
        printf '%s' "$home/${target:6}"
        return 0
    fi

    printf '%s' "$target"
}

resolve_existing_path() {
    local target="$1"

    if [[ -z "$target" ]]; then
        return 0
    fi

    if [[ -e "$target" || -L "$target" ]]; then
        readlink -f "$target" 2>/dev/null || printf '%s' "$target"
        return 0
    fi

    printf '%s' "$target"
}

read_json_string_field() {
    local file="$1"
    local field="$2"
    local line=""
    local value=""

    if [[ ! -f "$file" ]]; then
        return 0
    fi

    line="$(grep -E "\"${field}\"[[:space:]]*:" "$file" | head -n 1 || true)"
    if [[ -z "$line" ]]; then
        return 0
    fi

    if grep -Eq "\"${field}\"[[:space:]]*:[[:space:]]*null" <<<"$line"; then
        return 0
    fi

    value="$(sed -n 's/^[[:space:]]*.*"'"${field}"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' <<<"$line")"
    if [[ -n "$value" ]]; then
        printf '%s' "$value"
    fi
}

read_configured_data_directory() {
    local home="$1"
    local preferences="$home/.local/share/projectx/config/preferences.json"
    local configured=""

    if [[ ! -f "$preferences" ]]; then
        return 0
    fi

    configured="$(read_json_string_field "$preferences" "data_directory")"
    if [[ -n "$configured" ]]; then
        printf '%s' "$configured"
    fi
}

is_valid_projectx_data_root() {
    local target="$1"
    local marker="$target/.projectx-data-root"
    local schema=""

    [[ -d "$target" && -f "$marker" ]] || return 1

    if ! grep -q '"product"[[:space:]]*:[[:space:]]*"Project X"' "$marker"; then
        return 1
    fi

    schema="$(
        grep -E '"schema"[[:space:]]*:' "$marker" | head -n 1 \
            | sed -n 's/.*"schema"[[:space:]]*:[[:space:]]*\([0-9][0-9]*\).*/\1/p'
    )"
    [[ -n "$schema" && "$schema" -ge 1 ]]
}

is_safe_data_root_removal() {
    local home="$1"
    local target="$2"
    local resolved=""

    if [[ -z "$target" ]]; then
        return 1
    fi

    resolved="$(resolve_existing_path "$target")"

    case "$resolved" in
        /|/home|/usr|/etc|/var|/tmp)
            return 1
            ;;
    esac

    if [[ "$resolved" == "$home" ]]; then
        return 1
    fi

    return 0
}

remove_configured_data_root_from_value() {
    local home="$1"
    local configured="$2"
    local expanded=""
    local resolved=""

    if [[ -z "$configured" ]]; then
        return 0
    fi

    expanded="$(expand_user_path "$home" "$configured")"
    resolved="$(resolve_existing_path "$expanded")"

    log "Configured data_directory resolved to: $resolved"

    if ! is_safe_data_root_removal "$home" "$resolved"; then
        warn "Skipping unsafe configured data directory: $configured"
        return 0
    fi

    if ! is_valid_projectx_data_root "$resolved"; then
        warn "Skipping configured path without a valid Project X marker: $configured"
        return 0
    fi

    log "Removing configured Project X data root: $resolved"
    remove_path "$resolved"
}

cache_configured_data_roots() {
    local home=""
    local configured=""
    local preferences=""

    CONFIGURED_DATA_ROOTS=()

    while IFS= read -r home; do
        [[ -n "$home" ]] || continue
        preferences="$home/.local/share/projectx/config/preferences.json"
        configured="$(read_configured_data_directory "$home")"
        if [[ -n "$configured" ]]; then
            CONFIGURED_DATA_ROOTS+=("${home}|${configured}")
            log "Queued configured data root for removal (${home}): ${configured}"
        elif [[ -f "$preferences" ]]; then
            log "Bootstrap preferences found but data_directory is unset in $preferences"
        else
            log "No bootstrap preferences file at $preferences"
        fi
    done < <(collect_target_users)
}

remove_cached_configured_data_roots() {
    local entry=""
    local home=""
    local configured=""

    for entry in "${CONFIGURED_DATA_ROOTS[@]}"; do
        home="${entry%%|*}"
        configured="${entry#*|}"
        remove_configured_data_root_from_value "$home" "$configured"
    done
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
    remove_path "$home/.local/share/applications/projectx-uninstall.desktop"
    remove_path "$home/.local/bin/projectx"
    remove_path "$home/.local/bin/projectx-uninstall"

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
    remove_path "$home/.cache/projectx"
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
    remove_path "/usr/share/applications/projectx-uninstall.desktop"
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

needs_privileged_removal() {
    deb_package_present || \
        [[ -d /opt/projectx ]] || \
        [[ -x /usr/bin/projectx ]] || \
        [[ -x /usr/bin/projectx-uninstall ]] || \
        [[ -f /usr/share/applications/projectx.desktop ]] || \
        [[ -f /usr/share/applications/projectx-uninstall.desktop ]]
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
        die "Removing the ${PACKAGE_NAME} package requires root."
    fi

    log "Removing Debian package: ${PACKAGE_NAME}"
    if dpkg --purge "$PACKAGE_NAME"; then
        return 0
    fi

    warn "dpkg --purge ${PACKAGE_NAME} failed."
    return 1
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

    if command -v xdg-desktop-menu >/dev/null 2>&1; then
        xdg-desktop-menu forceupdate 2>/dev/null || true
    fi

    if [[ "$EUID" -eq 0 ]] && command -v update-menus >/dev/null 2>&1; then
        update-menus 2>/dev/null || true
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

gui_command() {
    if command -v zenity >/dev/null 2>&1; then
        printf 'zenity'
        return 0
    fi

    if command -v kdialog >/dev/null 2>&1; then
        printf 'kdialog'
        return 0
    fi

    return 1
}

gui_user() {
    if [[ -n "${PROJECTX_UNINSTALL_USER:-}" ]]; then
        printf '%s' "$PROJECTX_UNINSTALL_USER"
        return 0
    fi

    if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != "root" ]]; then
        printf '%s' "$SUDO_USER"
        return 0
    fi

    if [[ -n "${USER:-}" && "$USER" != "root" ]]; then
        printf '%s' "$USER"
        return 0
    fi

    return 1
}

run_gui_dialog() {
    local tool
    tool="$(gui_command)" || return 1

    local gui_user=""
    if gui_user="$(gui_user)"; then
        sudo -u "$gui_user" \
            DISPLAY="${DISPLAY:-:0}" \
            XAUTHORITY="${XAUTHORITY:-$(user_home_dir "$gui_user")/.Xauthority}" \
            DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
            "$tool" "$@"
        return $?
    fi

    "$tool" "$@"
}

confirm_uninstall_dialog() {
    local tool="${1:-}"

    case "$tool" in
        zenity)
            run_gui_dialog \
                --question \
                --title="Project X" \
                --text="Are you sure you want to completely remove Project X?\n\nThis will remove the application, your configuration, and all Project X data from this computer.\n\nThis action cannot be undone." \
                --ok-label="Uninstall" \
                --cancel-label="Cancel" \
                --width=480
            ;;
        kdialog)
            run_gui_dialog \
                --title "Project X" \
                --yesno "Are you sure you want to completely remove Project X?\n\nThis will remove the application, your configuration, and all Project X data from this computer.\n\nThis action cannot be undone." \
                --yes-label "Uninstall" \
                --no-label "Cancel"
            ;;
        *)
            return 1
            ;;
    esac
}

confirm_remove_user_data_dialog() {
    local tool="${1:-}"
    local message=(
        "A Project X felhasználói adatai is törlődjenek?"
        ""
        "Ha az Igen gombot választod, a Project X által létrehozott összes mappa, a hajóadatok, valamint minden összegyűjtött és mentett információ végleg törlődik a számítógépről."
        ""
        "Ha a Nem gombot választod, az adataid megmaradnak, és a Project X következő telepítésekor ott folytathatod a használatát, ahol abbahagytad."
    )
    local text=""
    local line

    for line in "${message[@]}"; do
        if [[ -z "$text" ]]; then
            text="$line"
        else
            text+=$'\n'"$line"
        fi
    done

    case "$tool" in
        zenity)
            run_gui_dialog \
                --question \
                --title="Project X" \
                --text="$text" \
                --ok-label="Igen" \
                --cancel-label="Nem" \
                --width=480
            ;;
        kdialog)
            run_gui_dialog \
                --title "Project X" \
                --yesno "$text" \
                --yes-label "Igen" \
                --no-label "Nem"
            ;;
        *)
            return 1
            ;;
    esac
}

show_success_dialog() {
    local tool="${1:-}"

    case "$tool" in
        zenity)
            run_gui_dialog \
                --info \
                --title="Project X" \
                --text="Project X has been successfully removed from your computer." \
                --ok-label="OK" \
                --width=460
            ;;
        kdialog)
            run_gui_dialog \
                --title "Project X" \
                --msgbox "Project X has been successfully removed from your computer." \
                --ok-label "OK"
            ;;
        *)
            return 1
            ;;
    esac
}

show_error_dialog() {
    local message="$1"
    local tool=""

    if tool="$(gui_command)"; then
        case "$tool" in
            zenity)
                run_gui_dialog \
                    --error \
                    --title="Project X" \
                    --text="$message" \
                    --ok-label="OK" \
                    --width=480
                ;;
            kdialog)
                run_gui_dialog \
                    --title "Project X" \
                    --error "$message"
                ;;
        esac
        return 0
    fi

    printf 'Error: %s\n' "$message" >&2
}

confirm_uninstall() {
    if [[ "$ASSUME_YES" -eq 1 || "$DRY_RUN" -eq 1 || "$SELF_TEST" -eq 1 || "$PRIVILEGED_ONLY" -eq 1 ]]; then
        return 0
    fi

    local tool=""
    if tool="$(gui_command)"; then
        if ! confirm_uninstall_dialog "$tool"; then
            exit 0
        fi
        return 0
    fi

    log "Project X Uninstall"
    log ""
    log "Are you sure you want to completely remove Project X?"
    log "This will remove the application, your configuration, and all Project X data."
    log "This action cannot be undone."
    log ""
    printf 'Type Uninstall to continue, or press Enter to cancel: '
    local reply
    read -r reply
    if [[ "$reply" != "Uninstall" ]]; then
        log "Uninstall cancelled."
        exit 0
    fi
}

confirm_remove_user_data() {
    if [[ "$ASSUME_YES" -eq 1 || "$DRY_RUN" -eq 1 || "$SELF_TEST" -eq 1 || "$PRIVILEGED_ONLY" -eq 1 ]]; then
        REMOVE_USER_DATA=1
        return 0
    fi

    local tool=""
    if tool="$(gui_command)"; then
        if confirm_remove_user_data_dialog "$tool"; then
            REMOVE_USER_DATA=1
        else
            REMOVE_USER_DATA=0
        fi
        return 0
    fi

    log ""
    log "A Project X felhasználói adatai is törlődjenek?"
    log ""
    log "Ha az Igen gombot választod, a Project X által létrehozott összes mappa, a hajóadatok, valamint minden összegyűjtött és mentett információ végleg törlődik a számítógépről."
    log ""
    log "Ha a Nem gombot választod, az adataid megmaradnak, és a Project X következő telepítésekor ott folytathatod a használatát, ahol abbahagytad."
    log ""
    printf 'Válasz (Igen/Nem) [Nem]: '
    local reply
    read -r reply
    case "$reply" in
        Igen|igen|I|i|Yes|yes|Y|y)
            REMOVE_USER_DATA=1
            ;;
        *)
            REMOVE_USER_DATA=0
            ;;
    esac
}

show_uninstall_complete() {
    if [[ "$DRY_RUN" -eq 1 || "$SELF_TEST" -eq 1 || "$PRIVILEGED_ONLY" -eq 1 ]]; then
        return 0
    fi

    local tool=""
    if tool="$(gui_command)"; then
        show_success_dialog "$tool" || true
        return 0
    fi

    log ""
    log "Project X has been successfully removed from your computer."
}

run_privileged_uninstall() {
    if [[ "$EUID" -ne 0 ]]; then
        die "Privileged uninstall requires root."
    fi

    if deb_package_present; then
        if ! remove_deb_package; then
            return 1
        fi
    fi

    remove_system_artifacts
    refresh_desktop_integration
    return 0
}

run_privileged_phase() {
    if [[ "$DRY_RUN" -eq 1 ]]; then
        log "[dry-run] privileged removal (package and system files)"
        remove_deb_package
        return 0
    fi

    if [[ "$EUID" -eq 0 ]]; then
        run_privileged_uninstall
        return $?
    fi

    if ! command -v pkexec >/dev/null 2>&1; then
        show_error_dialog \
            "Administrator privileges are required to remove Project X from your computer.\n\npkexec is not available on this system."
        return 1
    fi

    local launcher="$SCRIPT_PATH"
    if [[ ! -x "$launcher" ]]; then
        launcher="/usr/bin/projectx-uninstall"
    fi

    if [[ ! -x "$launcher" ]]; then
        show_error_dialog \
            "Administrator privileges are required to remove Project X from your computer.\n\nThe uninstaller could not be located."
        return 1
    fi

    local gui_user=""
    gui_user="$(gui_user)" || gui_user="$USER"

    local pkexec_status=0
    if pkexec env \
        DISPLAY="${DISPLAY:-:0}" \
        XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}" \
        DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
        PROJECTX_UNINSTALL_USER="${gui_user}" \
        "$launcher" --privileged-only --yes; then
        return 0
    fi
    pkexec_status=$?

    if [[ "$pkexec_status" -eq 127 || "$pkexec_status" -eq 126 ]]; then
        show_error_dialog \
            "Project X could not be completely removed.\n\nAdministrator approval is required to remove the installed package and system files.\n\nIf you cancelled the password prompt, no system changes were made."
        return 1
    fi

    show_error_dialog \
        "Project X could not be completely removed.\n\nThe Debian package removal failed.\n\nThe installed package may still be present."
    return 1
}

run_user_uninstall() {
    local home

    stop_projectx_processes
    discover_appimages "$HOME"

    if [[ "$REMOVE_USER_DATA" -eq 1 ]]; then
        cache_configured_data_roots
        remove_cached_configured_data_roots
        while IFS= read -r home; do
            [[ -n "$home" ]] || continue
            log "Removing user data for: $home"
            remove_user_state "$home"
        done < <(collect_target_users)
    elif [[ "$DRY_RUN" -eq 1 ]]; then
        log "[dry-run] keep Project X user data"
    else
        log "Keeping Project X user data."
    fi

    remove_appimages
}

run_uninstall() {
    run_user_uninstall

    if [[ "$SELF_TEST" -eq 1 ]]; then
        refresh_desktop_integration
        return 0
    fi

    if needs_privileged_removal; then
        if ! run_privileged_phase; then
            exit 1
        fi
    fi

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
        "$HOME/Project X/config" \
        "$HOME/.local/bin" \
        "$HOME/.local/share/applications" \
        "$HOME/.local/share/icons/hicolor/256x256/apps" \
        "$HOME/.config/autostart" \
        "$HOME/Desktop" \
        "$HOME/Downloads" \
        "$HOME/unrelated-backup"

    cat > "$HOME/Project X/.projectx-data-root" <<'EOF'
{"product":"Project X","schema":1,"created":"2026-01-01T00:00:00+00:00","uuid":"self-test"}
EOF
    printf '%s\n' 'configured-op' > "$HOME/Project X/config/observation_points.json"
    printf '%s\n' "{\"language\":\"en\",\"data_directory\":\"~/Project X\"}" > "$HOME/.local/share/projectx/config/preferences.json"
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
        "$HOME/Project X"
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

    if [[ "$PRIVILEGED_ONLY" -eq 1 ]]; then
        if ! run_privileged_uninstall; then
            exit 1
        fi
        exit 0
    fi

    confirm_uninstall
    confirm_remove_user_data
    run_uninstall
    show_uninstall_complete
    log "${APP_NAME} uninstall complete."
}

main "$@"
