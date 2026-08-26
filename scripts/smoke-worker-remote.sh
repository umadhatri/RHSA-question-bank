#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BASE_IMAGE="${RHSA_BASE_IMAGE:-cyberrange/rhsa-base:0.3}"
WORKER_VERSION="${RHSA_WORKER_VERSION:-0.4.1}"
OVERRIDE_IMAGE="${RHSA_REMOTE_SMOKE_IMAGE:-cyberrange/rhsa-base:remote-smoke}"
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

docker tag "$BASE_IMAGE" "$OVERRIDE_IMAGE"
"$ROOT/scripts/build-worker.sh"

TMP="$(mktemp -d)"
NET="rhsa-worker-remote-$RANDOM-$$"
STORE="rhsa-object-store-$RANDOM-$$"
cleanup() {
  docker rm -f "$STORE" >/dev/null 2>&1 || true
  docker network rm "$NET" >/dev/null 2>&1 || true
  docker image rm "$OVERRIDE_IMAGE" >/dev/null 2>&1 || true
  rm -rf "$TMP"
}
trap cleanup EXIT

cp "$ROOT/examples/student_good.sh" "$TMP/good.sh"
cp "$ROOT/examples/student_bad.sh" "$TMP/bad.sh"

cat > "$TMP/mock-object-store.py" <<'PY'
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path("/srv")
ALLOWED_GET = {"/good.sh": "good.sh", "/bad.sh": "bad.sh"}
ALLOWED_PUT = {"/good.json": "good.json", "/bad.json": "bad.json"}

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlparse(self.path).path
        name = ALLOWED_GET.get(path)
        if not name:
            self.send_error(404)
            return
        data = (ROOT / name).read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/x-shellscript")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_PUT(self):
        path = urlparse(self.path).path
        name = ALLOWED_PUT.get(path)
        if not name:
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        (ROOT / name).write_bytes(self.rfile.read(length))
        self.send_response(200)
        self.end_headers()

    def log_message(self, _format, *_args):
        return

ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
PY

docker network create "$NET" >/dev/null

docker run -d --rm \
  --name "$STORE" \
  --network "$NET" \
  -v "$TMP:/srv" \
  --entrypoint python3 \
  "$WORKER_IMAGE" \
  /srv/mock-object-store.py >/dev/null

# Give the tiny object-store server a moment to bind before the first GET.
sleep 1

run_remote_worker() {
  local input_name="$1"
  local output_name="$2"

  docker run --rm \
    --network "$NET" \
    -v "${DOCKER_SOCKET}:/var/run/docker.sock" \
    "$WORKER_IMAGE" \
    --lab-id RHSA-USERS-001 \
    --submission-url "http://${STORE}:8080/${input_name}" \
    --result-url "http://${STORE}:8080/${output_name}" \
    --base-image "$OVERRIDE_IMAGE" \
    --seed "$SEED"
}

echo
echo "=== Remote worker contract: correct submission ==="
run_remote_worker good.sh good.json

echo
echo "=== Remote worker contract: intentionally broken submission ==="
run_remote_worker bad.sh bad.json

python3 - "$TMP/good.json" "$TMP/bad.json" <<'PY'
import json
import sys
from pathlib import Path

good = json.loads(Path(sys.argv[1]).read_text())
bad = json.loads(Path(sys.argv[2]).read_text())

assert good["score"] == 100, good
assert good["passed"] is True, good
assert good["metadata"]["worker"]["version"] == "0.2.0", good
assert good["metadata"]["worker"]["submission_transport"] == "http", good
assert good["metadata"]["worker"]["result_transport"] == "http", good
assert good["metadata"]["image"] == "cyberrange/rhsa-base:remote-smoke", good

assert bad["score"] == 60, bad
assert bad["passed"] is False, bad
assert bad["metadata"]["worker"]["version"] == "0.2.0", bad
assert bad["metadata"]["worker"]["submission_transport"] == "http", bad
assert bad["metadata"]["worker"]["result_transport"] == "http", bad

print("Remote worker result assertions passed.")
PY

echo
echo "Remote grading-worker contract smoke test completed."
