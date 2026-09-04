#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"
: "${BUILD_A:?BUILD_A is required}"
: "${BUILD_B:?BUILD_B is required}"

output_a="/workspace/dynamic_a_${TEST_TOKEN}.txt"
output_b="/workspace/dynamic_b_${TEST_TOKEN}.txt"
producer_a="/workspace/producer_a_${TEST_TOKEN}"
producer_b="/workspace/producer_b_${TEST_TOKEN}"
formatter="/workspace/formatter_${TEST_TOKEN}"

rm -f -- "$producer_a" "$producer_b" "$formatter"

printf 'STALE A %s\n' "$TEST_TOKEN" > "$output_a"
printf 'STALE B %s\n' "$TEST_TOKEN" > "$output_b"

cat > "$producer_a" <<EOF_A
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'alpha-${TEST_TOKEN} build-${BUILD_A} [ready] \$literal *'
EOF_A

cat > "$producer_b" <<EOF_B
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'beta-${TEST_TOKEN} build-${BUILD_B} [ready] \$literal *'
EOF_B

cat > "$formatter" <<'FORMATTER'
#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || {
    printf 'expected exactly one argument, got %d\n' "$#" >&2
    exit 23
}

printf 'CAPTURED=%s\n' "$1"
FORMATTER

chmod 0755 "$producer_a" "$producer_b" "$formatter"
