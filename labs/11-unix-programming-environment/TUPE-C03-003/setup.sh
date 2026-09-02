#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"

src="/workspace/quote lab ${TEST_TOKEN} *"
output="/workspace/quote report ${TEST_TOKEN} ?.txt"

rm -rf -- \
  "$src" \
  "/workspace/quote lab ${TEST_TOKEN} A" \
  "/workspace/quote lab ${TEST_TOKEN} B"

mkdir -p -- \
  "$src" \
  "/workspace/quote lab ${TEST_TOKEN} A" \
  "/workspace/quote lab ${TEST_TOKEN} B"

printf 'STALE REPORT %s\n' "$TEST_TOKEN" > "$output"

printf 'Customer record %s with spaces\n' "$TEST_TOKEN" \
  > "$src/customer name.txt"

printf 'Price tier %s dollar-four\n' "$TEST_TOKEN" \
  > "$src/price\$4.txt"

printf 'Pattern literal %s star\n' "$TEST_TOKEN" \
  > "$src/pattern*.txt"

printf 'Question literal %s mark\n' "$TEST_TOKEN" \
  > "$src/question?.txt"

# Decoys make accidental wildcard expansion observably wrong.
printf 'DECOY customer underscore %s\n' "$TEST_TOKEN" \
  > "$src/customer_name.txt"

printf 'DECOY price no dollar %s\n' "$TEST_TOKEN" \
  > "$src/price4.txt"

printf 'DECOY price missing parameter %s\n' "$TEST_TOKEN" \
  > "$src/price.txt"

printf 'DECOY pattern A %s\n' "$TEST_TOKEN" \
  > "$src/patternA.txt"

printf 'DECOY pattern B %s\n' "$TEST_TOKEN" \
  > "$src/patternB.txt"

printf 'DECOY question one %s\n' "$TEST_TOKEN" \
  > "$src/question1.txt"

printf 'DECOY question X %s\n' "$TEST_TOKEN" \
  > "$src/questionX.txt"
