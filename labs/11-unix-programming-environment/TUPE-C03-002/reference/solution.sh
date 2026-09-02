#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 2 ]] || {
    echo "Usage: select_patterns.sh SOURCE_DIRECTORY OUTPUT_FILE" >&2
    exit 2
}

src=$1
output=$2

[[ -d "$src" ]] || {
    echo "Source directory does not exist: $src" >&2
    exit 2
}

shopt -s nullglob

emit_names() {
    local path
    for path in "$@"; do
        [[ -f "$path" ]] || continue
        basename -- "$path"
    done | sort
}

{
    printf '[SINGLE_CHAR_LOGS]\n'
    emit_names "$src"/app?.log

    printf '\n[NUMBERED_REPORTS]\n'
    emit_names "$src"/report[0-9].txt

    printf '\n[BACKUPS]\n'
    emit_names "$src"/*.old
} > "$output"
