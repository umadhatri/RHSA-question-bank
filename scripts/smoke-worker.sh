#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_IMAGE="cyberrange/rhsa-base:0.3"
WORKER_VERSION="${RHSA_WORKER_VERSION:-0.4.1}"
WORKER_IMAGE="cyberrange/rhsa-grading-worker:${WORKER_VERSION}"
DOCKER_SOCKET="${DOCKER_SOCKET:-/var/run/docker.sock}"
SEED="${RHSA_SMOKE_SEED:-424242}"

for cmd in docker python3; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: ${cmd} is required." >&2
    exit 1
  fi
done

if ! docker info >/dev/null 2>&1; then
  echo "ERROR: Docker daemon is not available." >&2
  exit 1
fi

if ! docker image inspect "$BASE_IMAGE" >/dev/null 2>&1; then
  "$ROOT/scripts/build-base.sh"
fi

"$ROOT/scripts/build-worker.sh"

# The trusted worker must contain hidden graders but not instructor reference
# answers. The untrusted sandbox must contain neither the question bank nor grader.
docker run --rm --entrypoint sh "$WORKER_IMAGE" -c \
  'test -f /opt/question-bank/labs/03-users-groups/RHSA-USERS-001/grader.py && test ! -e /opt/question-bank/labs/03-users-groups/RHSA-USERS-001/reference'

docker run --rm "$BASE_IMAGE" sh -c 'test ! -e /opt/question-bank'

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

run_worker() {
  local submission="$1"
  local output_name="$2"

  docker run --rm \
    --network none \
    -v "${DOCKER_SOCKET}:/var/run/docker.sock" \
    -v "${submission}:/job/submission.sh:ro" \
    -v "${TMP}:/job/output" \
    "$WORKER_IMAGE" \
    --lab-id RHSA-USERS-001 \
    --submission /job/submission.sh \
    --result "/job/output/${output_name}" \
    --seed "$SEED"
}

echo
echo "=== Worker: correct submission ==="
run_worker "$ROOT/examples/student_good.sh" good.json

echo
echo "=== Worker: intentionally broken submission ==="
run_worker "$ROOT/examples/student_bad.sh" bad.json

python3 - "$TMP/good.json" "$TMP/bad.json" <<'PY'
import json
import sys
from pathlib import Path

good = json.loads(Path(sys.argv[1]).read_text())
bad = json.loads(Path(sys.argv[2]).read_text())

assert good["score"] == 100, good
assert good["max_score"] == 100, good
assert good["passed"] is True, good
assert good["metadata"]["worker"]["version"] == "0.2.0", good

assert bad["score"] == 60, bad
assert bad["max_score"] == 100, bad
assert bad["passed"] is False, bad
assert bad["metadata"]["worker"]["version"] == "0.2.0", bad

print("Worker result assertions passed.")
PY

echo
echo "Grading-worker smoke test completed."
