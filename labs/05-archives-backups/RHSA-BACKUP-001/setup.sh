#!/usr/bin/env bash
set -euo pipefail
: "${TEST_TOKEN:?TEST_TOKEN is required}"

src="/opt/training/source_${TEST_TOKEN}"
dst="/var/backups/training_${TEST_TOKEN}"
rm -rf -- "$src" "$dst"
mkdir -p -- "$src/configs" "$src/data/nested"

printf 'Training backup %s\n' "$TEST_TOKEN" > "$src/README_${TEST_TOKEN}.txt"
printf 'listen_port=8443\nmode=training\n' > "$src/configs/app.conf"
printf 'user,role\nalice,admin\nbob,operator\n' > "$src/data/users.csv"
printf 'nested=%s\n' "$TEST_TOKEN" > "$src/data/nested/state.txt"
printf 'secret-marker=%s\n' "$TEST_TOKEN" > "$src/.backup_meta"
