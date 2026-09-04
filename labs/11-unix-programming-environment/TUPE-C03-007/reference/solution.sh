#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 4 ]] || {
    echo "Usage: environment_runner.sh OUTPUT_FILE TOOL_DIRECTORY CHILD_COMMAND SESSION_VALUE" >&2
    exit 2
}

output=$1
tool_dir=$2
child=$3
session=$4

PATH="$tool_dir:$PATH"
export PATH

TUPE_SESSION=$session
export TUPE_SESSION

"$child" > "$output"
