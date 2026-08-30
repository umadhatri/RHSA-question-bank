#!/usr/bin/env bash
set -euo pipefail

worker_pid="$(pgrep -x cr_worker || true)"

if [[ -z "$worker_pid" ]]; then
    echo "cr_worker is not running" >&2
    exit 1
fi

renice 10 -p "$worker_pid" >/dev/null

runaway_pid="$(pgrep -x cr_runaway || true)"

if [[ -n "$runaway_pid" ]]; then
    kill "$runaway_pid"
fi
