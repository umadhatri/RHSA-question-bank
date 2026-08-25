#!/usr/bin/env bash
set -euo pipefail
: "${TEST_TOKEN:?TEST_TOKEN is required}"

src="/workspace/source_${TEST_TOKEN}"
dst="/workspace/destination_${TEST_TOKEN}"
rm -rf -- "$src" "$dst"
mkdir -p -- "$src/leave_this_directory"

printf 'quarterly report %s\n' "$TEST_TOKEN" > "$src/report_${TEST_TOKEN}.txt"
printf 'meeting notes %s\n' "$TEST_TOKEN" > "$src/notes_${TEST_TOKEN}.txt"
printf 'service started\nservice stopped\n' > "$src/server_${TEST_TOKEN}.log"
printf 'audit event %s\n' "$TEST_TOKEN" > "$src/audit_${TEST_TOKEN}.log"
printf '\x00\x01training-%s\n' "$TEST_TOKEN" > "$src/payload_${TEST_TOKEN}.bin"
printf 'enabled=true\n' > "$src/config_${TEST_TOKEN}.conf"
printf 'hidden=%s\n' "$TEST_TOKEN" > "$src/.environment_${TEST_TOKEN}"
