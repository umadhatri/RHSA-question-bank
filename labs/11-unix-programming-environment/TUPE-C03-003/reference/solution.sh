#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 3 ]] || {
    echo "Usage: quote_report.sh SOURCE_DIRECTORY OUTPUT_FILE LABEL" >&2
    exit 2
}

src=$1
output=$2
label=$3

[[ -d "$src" ]] || {
    echo "Source directory does not exist: $src" >&2
    exit 2
}

customer=$(cat -- "$src/customer name.txt")
price=$(cat -- "$src/price\$4.txt")
pattern=$(cat -- "$src/pattern*.txt")
question=$(cat -- "$src/question?.txt")

{
    printf '[LABEL]\n'
    printf '%s\n' "$label"
    printf '\n[FILES]\n'
    printf 'customer=%s\n' "$customer"
    printf 'price=%s\n' "$price"
    printf 'pattern=%s\n' "$pattern"
    printf 'question=%s\n' "$question"
} > "$output"
