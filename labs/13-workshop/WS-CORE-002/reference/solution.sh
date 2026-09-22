#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 USERNAME GROUPNAME" >&2
    exit 2
fi

username=$1
groupname=$2

if ! getent group "$groupname" >/dev/null 2>&1; then
    groupadd "$groupname"
fi

if ! id "$username" >/dev/null 2>&1; then
    useradd -m -s /bin/bash "$username"
else
    usermod -s /bin/bash "$username"
fi

usermod -aG "$groupname" "$username"

mkdir -p "/srv/$groupname"
chown root:"$groupname" "/srv/$groupname"
chmod 2770 "/srv/$groupname"
