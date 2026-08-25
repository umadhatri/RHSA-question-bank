#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

./scripts/test.sh
./scripts/build-base.sh

run_reference() {
  local lab="$1"
  echo
  echo "=== Reference solution: ${lab} ==="
  python3 grader/runner.py \
    --lab "$lab" \
    --submission "$lab/reference/solution.sh" \
    --seed 424242
}

run_reference labs/01-shell-basics/RHSA-SHELL-001
run_reference labs/02-files-permissions/RHSA-FILE-001
run_reference labs/03-users-groups/RHSA-USERS-001
run_reference labs/04-text-processing/RHSA-TEXT-001
run_reference labs/05-archives-backups/RHSA-BACKUP-001

echo
echo "=== Intentionally broken canonical submission ==="
set +e
python3 grader/runner.py \
  --lab labs/03-users-groups/RHSA-USERS-001 \
  --submission examples/student_bad.sh \
  --seed 424242
rc=$?
set -e

if [[ "$rc" -ne 2 ]]; then
  echo "Expected broken submission to return exit code 2; got $rc" >&2
  exit 1
fi

echo
echo "Broken submission runner exit code: $rc"
echo "Question-bank smoke test completed."
