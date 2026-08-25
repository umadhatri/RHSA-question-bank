#!/usr/bin/env bash
set -euo pipefail

input=${1:?authentication log required}
output=${2:?output file required}
[[ -f "$input" ]] || { echo "Input log not found: $input" >&2; exit 2; }

awk '/Failed password/ { for (i=1; i<=NF; i++) if ($i == "from") print $(i+1) }' "$input" \
  | sort \
  | uniq -c \
  | awk '{print $1, $2}' \
  | sort -k1,1nr -k2,2 \
  > "$output"
