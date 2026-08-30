#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="cyberrange/rhsa-base:0.4"

echo "Building ${IMAGE} ..."
docker build -t "$IMAGE" "$ROOT/docker/base"
echo "Built ${IMAGE}"
