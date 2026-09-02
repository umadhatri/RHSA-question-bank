#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"

short_output="/workspace/short_manifest_${TEST_TOKEN}.txt"
long_output="/workspace/long_manifest_${TEST_TOKEN}.txt"

printf 'STALE SHORT %s\n' "$TEST_TOKEN" > "$short_output"
printf 'STALE LONG %s\n' "$TEST_TOKEN" > "$long_output"
