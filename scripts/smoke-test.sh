#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

./scripts/build-base.sh

echo
echo "=== Correct submission ==="
python3 grader/runner.py \
  --lab labs/01-users-groups/RHSA-USERS-001 \
  --submission examples/student_good.sh

echo
echo "=== Intentionally broken submission ==="
set +e
python3 grader/runner.py \
  --lab labs/01-users-groups/RHSA-USERS-001 \
  --submission examples/student_bad.sh
rc=$?
set -e

echo
echo "Broken submission runner exit code: $rc"
echo "Smoke test completed."
