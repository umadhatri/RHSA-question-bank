#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 3 ]] || {
    echo "Usage: make_notice.sh OUTPUT_FILE PROJECT OWNER" >&2
    exit 2
}

output=$1
project=$2
owner=$3

cat >"$output" <<EOF
BEGIN NOTICE
project=$project
owner=$owner
home-literal=\$HOME
command-literal=\$(date)
backtick-literal=\`whoami\`
END NOTICE
EOF
