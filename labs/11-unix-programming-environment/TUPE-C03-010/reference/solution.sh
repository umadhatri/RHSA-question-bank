#!/usr/bin/env bash
set -euo pipefail

[[ $# -ge 2 ]] || {
    echo "Usage: batch_report.sh OUTPUT_FILE INPUT_FILE..." >&2
    exit 2
}

output=$1
shift

: > "$output"

for file in "$@"; do
    name=$(basename -- "$file")
    lines=$(wc -l < "$file")

    printf 'FILE=%s\n' "$name" >> "$output"
    printf 'LINES=%d\n' "$lines" >> "$output"
done
