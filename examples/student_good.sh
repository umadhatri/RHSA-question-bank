#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 2 ]] || exit 2
user_name=$1
group_name=$2

getent group "$group_name" >/dev/null 2>&1 || groupadd "$group_name"
id "$user_name" >/dev/null 2>&1 || useradd -m -s /bin/bash "$user_name"
usermod -s /bin/bash -aG "$group_name" "$user_name"
mkdir -p "/srv/$group_name"
chown root:"$group_name" "/srv/$group_name"
chmod 2770 "/srv/$group_name"
