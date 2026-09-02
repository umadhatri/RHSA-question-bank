#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || {
    echo "Usage: pipeline_report.sh OUTPUT_FILE" >&2
    exit 2
}

output=$1

(tupe-source-a; tupe-source-b) \
    | grep '^ERROR ' \
    | sort -u \
    > "$output"
