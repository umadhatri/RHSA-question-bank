#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 USERNAME" >&2
    exit 2
fi

username=$1

if ! id "$username" >/dev/null 2>&1; then
    echo "User does not exist: $username" >&2
    exit 1
fi

dropin="/etc/sudoers.d/cyberrange-$username"
tmp="$(mktemp)"

cleanup() {
    rm -f "$tmp"
}
trap cleanup EXIT

printf '%s ALL=(root) NOPASSWD: /usr/local/sbin/cyberrange-maintenance\n' \
    "$username" > "$tmp"

chown root:root "$tmp"
chmod 0440 "$tmp"

visudo -cf "$tmp" >/dev/null

install \
    -o root \
    -g root \
    -m 0440 \
    "$tmp" \
    "$dropin"

visudo -cf /etc/sudoers >/dev/null
