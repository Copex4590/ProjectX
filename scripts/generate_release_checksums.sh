#!/usr/bin/env bash
# ============================================================================
# Project X — Generate per-platform SHA256SUMS (SAVE-085)
# ============================================================================
# Linux public release:  release/linux/SHA256SUMS  (ProjectX.AppImage, ProjectX.deb)
# Windows public release: release/windows/SHA256SUMS (ProjectX-Setup.exe)

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WINDOWS_DIR="${ROOT}/release/windows"
LINUX_DIR="${ROOT}/release/linux"

write_platform_sums() {
    local platform_dir="$1"
    local platform_name="$2"
    local sums_file="${platform_dir}/SHA256SUMS"

    if [[ ! -d "$platform_dir" ]]; then
        return 0
    fi

    shopt -s nullglob
    local artifacts=()
    local file base
    for file in "$platform_dir"/*; do
        [[ -f "$file" ]] || continue
        base="$(basename "$file")"
        case "$base" in
            README.md | SHA256SUMS) continue ;;
        esac
        artifacts+=("$file")
    done
    shopt -u nullglob

    if [[ "${#artifacts[@]}" -eq 0 ]]; then
        echo "[WARN] No ${platform_name} artifacts under ${platform_dir#${ROOT}/}."
        return 0
    fi

    : > "$sums_file"
    for file in "${artifacts[@]}"; do
        base="$(basename "$file")"
        hash="$(sha256sum "$file" | awk '{print $1}')"
        printf '%s  %s\n' "$hash" "$base" >> "$sums_file"
        echo "[OK] ${platform_name}: ${base}"
    done

    echo "[OK] ${platform_name} checksums: ${sums_file#${ROOT}/}"

    local web_dir=""
    case "$platform_name" in
        linux) web_dir="${ROOT}/website/downloads/linux" ;;
        windows) web_dir="${ROOT}/website/downloads/windows" ;;
    esac
    if [[ -n "$web_dir" && -d "$web_dir" ]]; then
        cp -f "$sums_file" "${web_dir}/SHA256SUMS"
        echo "[OK] Website copy: ${web_dir#${ROOT}/}/SHA256SUMS"
    fi
}

echo "Generating per-platform SHA256SUMS..."

write_platform_sums "$LINUX_DIR" "linux"
write_platform_sums "$WINDOWS_DIR" "windows"

echo "Checksum generation complete."
