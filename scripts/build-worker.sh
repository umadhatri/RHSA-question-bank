#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION="${RHSA_WORKER_VERSION:-0.4.1}"
IMAGE="cyberrange/rhsa-grading-worker:${VERSION}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker CLI is required." >&2
  exit 1
fi

REVISION="$(git -C "$ROOT" rev-parse --short=12 HEAD 2>/dev/null || echo unknown)"
REV_IMAGE="cyberrange/rhsa-grading-worker:${REVISION}"

echo "Building ${IMAGE} from question-bank revision ${REVISION} ..."
docker build \
  -f "$ROOT/docker/worker/Dockerfile" \
  --build-arg "QUESTION_BANK_REVISION=${REVISION}" \
  -t "$IMAGE" \
  -t "$REV_IMAGE" \
  "$ROOT"

echo "Built ${IMAGE}"
echo "Immutable local tag: ${REV_IMAGE}"
