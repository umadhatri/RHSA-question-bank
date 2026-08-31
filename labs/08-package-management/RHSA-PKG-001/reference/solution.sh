#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 RPM_FILE" >&2
    exit 2
fi

rpm_file=$1

if [[ ! -f "$rpm_file" ]]; then
    echo "RPM file does not exist: $rpm_file" >&2
    exit 1
fi

expected="$(
    rpm -qp \
        --queryformat '%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}' \
        "$rpm_file"
)"

installed="$(
    rpm -q cyberrange-monitor \
        --queryformat '%{NAME}|%{VERSION}|%{RELEASE}|%{ARCH}' \
        2>/dev/null || true
)"

if [[ "$installed" == "$expected" ]]; then
    exit 0
fi

rpm -Uvh "$rpm_file" >/dev/null
