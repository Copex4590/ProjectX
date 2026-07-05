#!/usr/bin/env bash
# ============================================================================
# Project X — Generate SHA256 checksums for release artifacts (SAVE-078)
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CHECKSUM_DIR="${ROOT}/release/checksums"
WINDOWS_DIR="${ROOT}/release/windows"
LINUX_DIR="${ROOT}/release/linux"

mkdir -p "$CHECKSUM_DIR"

echo "Generating SHA256 checksums in ${CHECKSUM_DIR} ..."

shopt -s nullglob
ARTIFACTS=()
for dir in "$WINDOWS_DIR" "$LINUX_DIR"; do
    for file in "$dir"/*; do
        [[ -f "$file" ]] || continue
        base="$(basename "$file")"
        case "$base" in
            README.md) continue ;;
        esac
        ARTIFACTS+=("$file")
    done
done
shopt -u nullglob

if [[ "${#ARTIFACTS[@]}" -eq 0 ]]; then
    echo "[WARN] No release artifacts found under release/windows/ or release/linux/."
    echo "       Build packages first, then re-run this script."
    exit 0
fi

COMBINED="${CHECKSUM_DIR}/SHA256SUMS"
: > "$COMBINED"

for file in "${ARTIFACTS[@]}"; do
    base="$(basename "$file")"
    rel="${file#${ROOT}/}"
    sha256sum "$file" > "${CHECKSUM_DIR}/${base}.sha256"
    sha256sum "$file" >> "$COMBINED"
    echo "[OK] ${base}.sha256 (${rel})"
done

echo "[OK] Combined checksums: ${COMBINED#${ROOT}/}"
