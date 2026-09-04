#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 3 ]] || {
    echo "Usage: dynamic_report.sh OUTPUT_FILE PRODUCER_COMMAND FORMATTER_COMMAND" >&2
    exit 2
}

output=$1
producer=$2
formatter=$3

value=$("$producer")
"$formatter" "$value" > "$output"
