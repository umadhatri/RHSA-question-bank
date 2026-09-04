#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"

dir="/workspace/batch_${TEST_TOKEN}"
output_short="/workspace/batch_short_${TEST_TOKEN}.txt"
output_long="/workspace/batch_long_${TEST_TOKEN}.txt"

rm -rf -- "$dir"
mkdir -p -- "$dir"

printf 'alpha-%s first\nalpha second\n' "$TEST_TOKEN" \
  > "$dir/alpha one.txt"

printf 'beta-%s first\nbeta second\nbeta third\n' "$TEST_TOKEN" \
  > "$dir/beta[2].txt"

printf 'gamma-%s only\n' "$TEST_TOKEN" \
  > "$dir/gamma*.txt"

printf 'delta-%s one\ndelta two\ndelta three\ndelta four\n' "$TEST_TOKEN" \
  > "$dir/delta dollar$.txt"

: > "$dir/epsilon-empty.txt"

printf 'DECOY-%s one\nDECOY two\nDECOY three\nDECOY four\nDECOY five\n' \
  "$TEST_TOKEN" > "$dir/decoy-not-supplied.txt"

chmod 0644 "$dir"/*

printf 'STALE SHORT %s\n' "$TEST_TOKEN" > "$output_short"
printf 'STALE LONG %s\n' "$TEST_TOKEN" > "$output_long"
