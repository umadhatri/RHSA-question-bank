#!/usr/bin/env bash
set -euo pipefail

src=${1:?source directory required}
dst=${2:?destination directory required}
archive=${3:?archive name required}
[[ -d "$src" ]] || { echo "Source directory does not exist: $src" >&2; exit 2; }

mkdir -p -- "$dst"
tar -czf "$dst/$archive" -C "$src" .
