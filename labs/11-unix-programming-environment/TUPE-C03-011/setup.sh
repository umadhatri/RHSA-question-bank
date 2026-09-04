#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"

source_dir="/workspace/bundle_sources_${TEST_TOKEN}"
hold_dir="/workspace/bundle_sources_hold_${TEST_TOKEN}"
extract_short="/workspace/extract_short_${TEST_TOKEN}"
extract_long="/workspace/extract_long_${TEST_TOKEN}"
bundle_short="/workspace/bundle_short_${TEST_TOKEN}.sh"
bundle_long="/workspace/bundle_long_${TEST_TOKEN}.sh"

rm -rf -- "$source_dir" "$hold_dir" "$extract_short" "$extract_long"
mkdir -p -- "$source_dir"

cat > "$source_dir/alpha note.txt" <<EOF_ALPHA
alpha-${TEST_TOKEN}
\$HOME must remain literal
\$(date) must remain literal
EOF
EOF_ALPHA

cat > "$source_dir/beta[2].conf" <<EOF_BETA
beta-${TEST_TOKEN}
backtick: \`whoami\`
single quote: 'alpha'
double quote: "beta"
backslash: \\
EOF_BETA

cat > "$source_dir/gamma*.txt" <<EOF_GAMMA
gamma-${TEST_TOKEN} first

middle blank line above
__TUPE_BUNDLE_3__
gamma final
EOF_GAMMA

cat > "$source_dir/delta dollar$.txt" <<EOF_DELTA
delta-${TEST_TOKEN}
END_BUNDLE
\$literal * [brackets]
EOF_DELTA

: > "$source_dir/epsilon-empty.txt"

cat > "$source_dir/decoy-not-supplied.txt" <<EOF_DECOY
DECOY-${TEST_TOKEN}
this file must never be bundled
EOF_DECOY

chmod 0644 "$source_dir"/*

printf 'STALE SHORT BUNDLE %s\n' "$TEST_TOKEN" > "$bundle_short"
printf 'STALE LONG BUNDLE %s\n' "$TEST_TOKEN" > "$bundle_long"
