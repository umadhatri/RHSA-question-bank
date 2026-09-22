#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"

tool_a="/workspace/tool_a_${TEST_TOKEN}"
tool_b="/workspace/tool_b_${TEST_TOKEN}"
decoy_dir="/workspace/decoy_bin_${TEST_TOKEN}"
legacy_dir="/workspace/legacy_bin_${TEST_TOKEN}"
probe="/workspace/environment_probe_${TEST_TOKEN}"
output_a="/workspace/environment_a_${TEST_TOKEN}.txt"
output_b="/workspace/environment_b_${TEST_TOKEN}.txt"

rm -rf -- "$tool_a" "$tool_b" "$decoy_dir" "$legacy_dir"
rm -f -- "$probe"

mkdir -p "$tool_a" "$tool_b" "$decoy_dir" "$legacy_dir"

printf 'STALE A %s\n' "$TEST_TOKEN" > "$output_a"
printf 'STALE B %s\n' "$TEST_TOKEN" > "$output_b"

cat > "$tool_a/range-tool" <<EOF_A
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'alpha-${TEST_TOKEN}'
EOF_A

cat > "$tool_b/range-tool" <<EOF_B
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'beta-${TEST_TOKEN}'
EOF_B

cat > "$decoy_dir/range-tool" <<EOF_DECOY
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'decoy-${TEST_TOKEN}'
EOF_DECOY

cat > "$legacy_dir/legacy-helper" <<EOF_LEGACY
#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' 'legacy-${TEST_TOKEN}'
EOF_LEGACY

cat > "$probe" <<'PROBE'
#!/usr/bin/env bash
set -u

resolved_tool=$(command -v range-tool 2>/dev/null || true)
tool_value=$(range-tool 2>/dev/null || true)
resolved_legacy=$(command -v legacy-helper 2>/dev/null || true)
legacy_value=$(legacy-helper 2>/dev/null || true)

printf 'SESSION=%s\n' "${TUPE_SESSION-<unset>}"
printf 'RESOLVED_TOOL=%s\n' "$resolved_tool"
printf 'TOOL_VALUE=%s\n' "$tool_value"
printf 'RESOLVED_LEGACY=%s\n' "$resolved_legacy"
printf 'LEGACY_VALUE=%s\n' "$legacy_value"
printf 'PATH=%s\n' "$PATH"
PROBE

chmod 0755 \
  "$tool_a/range-tool" \
  "$tool_b/range-tool" \
  "$decoy_dir/range-tool" \
  "$legacy_dir/legacy-helper" \
  "$probe"
