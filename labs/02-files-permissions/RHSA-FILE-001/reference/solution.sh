#!/usr/bin/env bash
set -euo pipefail

project=${1:?project directory required}
group=${2:?group name required}
getent group "$group" >/dev/null || { echo "Unknown group: $group" >&2; exit 2; }

mkdir -p -- "$project" "$project/archive"
touch -- "$project/README.txt"
chgrp -- "$group" "$project" "$project/README.txt" "$project/archive"
chmod 2770 "$project"
chmod 0660 "$project/README.txt"
chmod 2750 "$project/archive"
