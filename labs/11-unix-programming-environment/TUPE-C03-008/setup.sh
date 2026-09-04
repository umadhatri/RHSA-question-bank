#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"
: "${CODE_A:?CODE_A is required}"
: "${CODE_B:?CODE_B is required}"

stdout_a="/workspace/stdout_a_${TEST_TOKEN}.txt"
stderr_a="/workspace/stderr_a_${TEST_TOKEN}.txt"
stdout_b="/workspace/stdout_b_${TEST_TOKEN}.txt"
stderr_b="/workspace/stderr_b_${TEST_TOKEN}.txt"
emitter_a="/workspace/emitter_a_${TEST_TOKEN}"
emitter_b="/workspace/emitter_b_${TEST_TOKEN}"

rm -f -- "$emitter_a" "$emitter_b"

printf 'STALE STDOUT A %s\n' "$TEST_TOKEN" > "$stdout_a"
printf 'STALE STDERR A %s\n' "$TEST_TOKEN" > "$stderr_a"
printf 'STALE STDOUT B %s\n' "$TEST_TOKEN" > "$stdout_b"
printf 'STALE STDERR B %s\n' "$TEST_TOKEN" > "$stderr_b"

cat > "$emitter_a" <<EOF_A
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'OUT alpha-${TEST_TOKEN} code-${CODE_A} [ok] \$literal *'
printf '%s\n' 'ERR alpha-${TEST_TOKEN} code-${CODE_A} [warn] \$literal *' >&2
EOF_A

cat > "$emitter_b" <<EOF_B
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'OUT beta-${TEST_TOKEN} code-${CODE_B} [ok] \$literal *'
printf '%s\n' 'ERR beta-${TEST_TOKEN} code-${CODE_B} [warn] \$literal *' >&2
EOF_B

chmod 0755 "$emitter_a" "$emitter_b"
