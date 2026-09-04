#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 3 ]] || {
    echo "Usage: route_streams.sh STDOUT_FILE STDERR_FILE EMITTER_COMMAND" >&2
    exit 2
}

stdout_file=$1
stderr_file=$2
emitter=$3

"$emitter" >"$stdout_file" 2>"$stderr_file"
