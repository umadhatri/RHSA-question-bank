#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"
: "${LOG_START:?LOG_START is required}"
: "${REPORT_START:?REPORT_START is required}"

src="/workspace/patterns_${TEST_TOKEN}"
output="/workspace/pattern_report_${TEST_TOKEN}.txt"

rm -rf -- "$src"
mkdir -p -- "$src"

printf 'STALE REPORT %s\n' "$TEST_TOKEN" > "$output"

log_a=$LOG_START
log_b=$((LOG_START + 1))
log_c=$((LOG_START + 2))

report_a=$REPORT_START
report_b=$((REPORT_START + 1))
report_c=$((REPORT_START + 2))

touch -- \
  "$src/app${log_a}.log" \
  "$src/app${log_b}.log" \
  "$src/app${log_c}.log" \
  "$src/app${log_a}${log_b}.log" \
  "$src/app.log" \
  "$src/App${log_a}.log" \
  "$src/app${log_a}.txt" \
  "$src/.app${log_a}.log"

touch -- \
  "$src/report${report_a}.txt" \
  "$src/report${report_b}.txt" \
  "$src/report${report_c}.txt" \
  "$src/report${report_a}${report_b}.txt" \
  "$src/reportA.txt" \
  "$src/report-${report_a}.txt" \
  "$src/report${report_a}.log" \
  "$src/.report${report_a}.txt"

touch -- \
  "$src/config_${TEST_TOKEN}.old" \
  "$src/notes_${TEST_TOKEN}.old" \
  "$src/archive_${TEST_TOKEN}.old" \
  "$src/config_${TEST_TOKEN}.old.tmp" \
  "$src/notes_${TEST_TOKEN}.old.bak" \
  "$src/archive_${TEST_TOKEN}.OLD" \
  "$src/.secret_${TEST_TOKEN}.old"

mkdir -p -- \
  "$src/app${log_a}.log.directory" \
  "$src/report${report_a}.txt.directory"
