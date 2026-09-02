#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"

output="/workspace/error_report_${TEST_TOKEN}.txt"

# Deliberately seed the destination with stale data. A correct solution must
# replace the file rather than append to it.
printf 'STALE REPORT %s\n' "$TEST_TOKEN" > "$output"

cat > /usr/local/bin/tupe-source-a <<EOF
#!/usr/bin/env bash
printf '%s\n' \\
  'INFO source-a-${TEST_TOKEN} started' \\
  'ERROR alpha-${TEST_TOKEN} disk-threshold' \\
  'WARN source-a-${TEST_TOKEN} latency-high' \\
  'NOTICE embedded ERROR source-a-${TEST_TOKEN}' \\
  'ERROR shared-${TEST_TOKEN} authentication-retry'
EOF

cat > /usr/local/bin/tupe-source-b <<EOF
#!/usr/bin/env bash
printf '%s\n' \\
  'INFO source-b-${TEST_TOKEN} started' \\
  'ERROR beta-${TEST_TOKEN} queue-backlog' \\
  'ERROR shared-${TEST_TOKEN} authentication-retry' \\
  'DEBUG source-b-${TEST_TOKEN} diagnostic' \\
  'ERROR zeta-${TEST_TOKEN} service-unavailable'
EOF

chmod 0755 \
  /usr/local/bin/tupe-source-a \
  /usr/local/bin/tupe-source-b
