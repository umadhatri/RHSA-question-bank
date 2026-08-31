#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TEST_USERNAME:-}" ]]; then
    echo "TEST_USERNAME is required" >&2
    exit 1
fi

if id "$TEST_USERNAME" >/dev/null 2>&1; then
    echo "Generated test user already exists: $TEST_USERNAME" >&2
    exit 1
fi

useradd -m -s /bin/bash "$TEST_USERNAME"

home="$(
    getent passwd "$TEST_USERNAME" |
        cut -d: -f6
)"

group="$(
    id -gn "$TEST_USERNAME"
)"

uid="$(
    id -u "$TEST_USERNAME"
)"

gid="$(
    id -g "$TEST_USERNAME"
)"

key_work="/tmp/cyberrange-ssh-keys"
key_dir="/opt/cyberrange/keys"

mkdir -p "$key_work" "$key_dir"

ssh-keygen \
    -q \
    -t ed25519 \
    -N '' \
    -C "existing-${TEST_USERNAME}" \
    -f "$key_work/existing"

ssh-keygen \
    -q \
    -t ed25519 \
    -N '' \
    -C "supplied-${TEST_USERNAME}" \
    -f "$key_work/supplied"

install \
    -d \
    -o "$TEST_USERNAME" \
    -g "$group" \
    -m 0700 \
    "$home/.ssh"

install \
    -o "$TEST_USERNAME" \
    -g "$group" \
    -m 0600 \
    "$key_work/existing.pub" \
    "$home/.ssh/authorized_keys"

install \
    -o root \
    -g root \
    -m 0644 \
    "$key_work/supplied.pub" \
    "$key_dir/access_key.pub"

# Establish a known global daemon configuration state.
mkdir -p /etc/ssh/sshd_config.d
find /etc/ssh/sshd_config.d \
    -mindepth 1 \
    -maxdepth 1 \
    -type f \
    -delete

chown root:root /etc/ssh/sshd_config.d
chmod 0700 /etc/ssh/sshd_config.d

printf 'EXPECTED_UID=%s\n' "$uid"
printf 'EXPECTED_GID=%s\n' "$gid"
printf 'EXPECTED_HOME=%s\n' "$home"

printf 'EXISTING_KEY_B64=%s\n' \
    "$(base64 -w0 "$key_work/existing.pub")"

printf 'SUPPLIED_KEY_B64=%s\n' \
    "$(base64 -w0 "$key_work/supplied.pub")"

printf 'SOURCE_KEY_SHA256=%s\n' \
    "$(sha256sum "$key_dir/access_key.pub" | awk '{print $1}')"

printf 'SSHD_CONFIG_SHA256=%s\n' \
    "$(sha256sum /etc/ssh/sshd_config | awk '{print $1}')"

rm -rf "$key_work"
