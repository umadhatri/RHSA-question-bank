#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"

output_a="/workspace/notice_a_${TEST_TOKEN}.txt"
output_b="/workspace/notice_b_${TEST_TOKEN}.txt"

printf 'STALE NOTICE A %s\n' "$TEST_TOKEN" > "$output_a"
printf 'STALE NOTICE B %s\n' "$TEST_TOKEN" > "$output_b"
