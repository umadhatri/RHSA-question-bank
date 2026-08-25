#!/usr/bin/env bash
set -euo pipefail
: "${TEST_TOKEN:?TEST_TOKEN is required}" "${README_PRESENT:?README_PRESENT is required}"

group="proj_${TEST_TOKEN}"
project="/srv/project_${TEST_TOKEN}"

getent group "$group" >/dev/null || groupadd "$group"
rm -rf -- "$project"
mkdir -p -- "$project"
chown root:root "$project"
chmod 0755 "$project"
if [[ "$README_PRESENT" == "1" ]]; then
  printf 'Existing project notes for %s. Do not overwrite.\n' "$TEST_TOKEN" > "$project/README.txt"
  chown root:root "$project/README.txt"
  chmod 0644 "$project/README.txt"
fi
