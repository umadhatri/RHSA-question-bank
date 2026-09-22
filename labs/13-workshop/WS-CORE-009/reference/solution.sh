#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
    echo "Usage: $0 USERNAME HOUR MINUTE" >&2
    exit 2
fi

username=$1
hour=$2
minute=$3

if ! id "$username" >/dev/null 2>&1; then
    echo "User does not exist: $username" >&2
    exit 1
fi

if [[ ! "$hour" =~ ^([0-9]|1[0-9]|2[0-3])$ ]]; then
    echo "Invalid hour: $hour" >&2
    exit 1
fi

if [[ ! "$minute" =~ ^([0-9]|[1-5][0-9])$ ]]; then
    echo "Invalid minute: $minute" >&2
    exit 1
fi

cron_file="/etc/cron.d/cyberrange-maintenance"

job="$minute $hour * * * $username /usr/local/sbin/cyberrange-maintenance"

if ! grep -qxF -- "$job" "$cron_file"; then
    printf '%s\n' "$job" >> "$cron_file"
fi

chown root:root "$cron_file"
chmod 0644 "$cron_file"
