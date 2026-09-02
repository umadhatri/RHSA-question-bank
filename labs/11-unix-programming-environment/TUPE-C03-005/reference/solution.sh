#!/usr/bin/env bash
set -euo pipefail

[[ $# -ge 3 ]] || {
    echo "Usage: argument_manifest.sh OUTPUT_FILE LABEL ITEM [ITEM ...]" >&2
    exit 2
}

output=$1
label=$2
shift 2

{
    printf 'LABEL=%s\n' "$label"
    printf 'COUNT=%d\n' "$#"

    index=1

    for item in "$@"; do
        printf '%d=%s\n' "$index" "$item"
        index=$((index + 1))
    done
} > "$output"
