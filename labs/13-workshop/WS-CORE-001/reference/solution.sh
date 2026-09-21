#!/usr/bin/env bash
set -euo pipefail

src=${1:?source directory required}
dst=${2:?destination directory required}
[[ -d "$src" ]] || { echo "Source directory does not exist: $src" >&2; exit 2; }

mkdir -p -- "$dst/text" "$dst/logs" "$dst/other"
shopt -s nullglob dotglob
for path in "$src"/*; do
    [[ -f "$path" ]] || continue
    name=${path##*/}
    case "$name" in
        *.txt) target="$dst/text/" ;;
        *.log) target="$dst/logs/" ;;
        *)     target="$dst/other/" ;;
    esac
    mv -f -- "$path" "$target"
done
