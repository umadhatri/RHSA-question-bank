#!/usr/bin/env bash
set -euo pipefail

install -d -o root -g root -m 0755 /usr/local/libexec/cyberrange

install -o root -g root -m 0755 \
    /usr/bin/sleep \
    /usr/local/libexec/cyberrange/cr_runaway

install -o root -g root -m 0755 \
    /usr/bin/sleep \
    /usr/local/libexec/cyberrange/cr_worker

install -o root -g root -m 0755 \
    /usr/bin/sleep \
    /usr/local/libexec/cyberrange/cr_control

nohup /usr/local/libexec/cyberrange/cr_runaway 3600 \
    >/dev/null 2>&1 &
runaway_pid=$!

nohup /usr/local/libexec/cyberrange/cr_worker 3600 \
    >/dev/null 2>&1 &
worker_pid=$!

nohup /usr/local/libexec/cyberrange/cr_control 3600 \
    >/dev/null 2>&1 &
control_pid=$!

sleep 0.2

for pid in "$runaway_pid" "$worker_pid" "$control_pid"; do
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "Failed to initialize process PID $pid" >&2
        exit 1
    fi
done

printf 'RUNAWAY_PID=%s\n' "$runaway_pid"
printf 'WORKER_PID=%s\n' "$worker_pid"
printf 'CONTROL_PID=%s\n' "$control_pid"
