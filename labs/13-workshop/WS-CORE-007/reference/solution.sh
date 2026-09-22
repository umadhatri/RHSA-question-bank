#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
    echo "Usage: $0 USERNAME PUBLIC_KEY_FILE" >&2
    exit 2
fi

username=$1
key_file=$2

if ! id "$username" >/dev/null 2>&1; then
    echo "User does not exist: $username" >&2
    exit 1
fi

if [[ ! -f "$key_file" ]]; then
    echo "Public key file does not exist: $key_file" >&2
    exit 1
fi

ssh-keygen -l -f "$key_file" >/dev/null

home="$(
    getent passwd "$username" |
        cut -d: -f6
)"

group="$(
    id -gn "$username"
)"

ssh_dir="$home/.ssh"
authorized_keys="$ssh_dir/authorized_keys"

install \
    -d \
    -o "$username" \
    -g "$group" \
    -m 0700 \
    "$ssh_dir"

touch "$authorized_keys"

chown "$username:$group" "$authorized_keys"
chmod 0600 "$authorized_keys"

key="$(
    cat "$key_file"
)"

if ! grep -qxF -- "$key" "$authorized_keys"; then
    printf '%s\n' "$key" >> "$authorized_keys"
fi
