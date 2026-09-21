#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TEST_USERNAME:-}" ]]; then
    echo "TEST_USERNAME is required" >&2
    exit 1
fi

if [[ -z "${TEST_HOUR:-}" || -z "${TEST_MINUTE:-}" ]]; then
    echo "TEST_HOUR and TEST_MINUTE are required" >&2
    exit 1
fi

if id "$TEST_USERNAME" >/dev/null 2>&1; then
    echo "Generated test user already exists: $TEST_USERNAME" >&2
    exit 1
fi

useradd -m -s /bin/bash "$TEST_USERNAME"

uid="$(id -u "$TEST_USERNAME")"
gid="$(id -g "$TEST_USERNAME")"
home="$(
    getent passwd "$TEST_USERNAME" |
        cut -d: -f6
)"

install -d -o root -g root -m 0755 /usr/local/sbin

cat > /usr/local/sbin/cyberrange-maintenance <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf 'daily-maintenance-ok\n'
EOF

cat > /usr/local/sbin/cyberrange-weekly-audit <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

printf 'weekly-audit-ok\n'
EOF

chown root:root \
    /usr/local/sbin/cyberrange-maintenance \
    /usr/local/sbin/cyberrange-weekly-audit

chmod 0755 \
    /usr/local/sbin/cyberrange-maintenance \
    /usr/local/sbin/cyberrange-weekly-audit

install -d -o root -g root -m 0755 /etc/cron.d
install -d -o root -g root -m 0700 /var/spool/cron

# Establish a deterministic cron scope for hidden grading.
find /etc/cron.d     -mindepth 1     -maxdepth 1     -type f     -delete

find /var/spool/cron     -mindepth 1     -maxdepth 1     -type f     -delete

cron_file="/etc/cron.d/cyberrange-maintenance"
unrelated_file="/etc/cron.d/cyberrange-unrelated"

existing_line="17 3 * * 1 root /usr/local/sbin/cyberrange-weekly-audit"
unrelated_line="23 4 * * 6 root /usr/bin/true"

printf '%s\n' "$existing_line" > "$cron_file"
printf '%s\n' "$unrelated_line" > "$unrelated_file"

chown root:root "$cron_file" "$unrelated_file"
chmod 0644 "$cron_file" "$unrelated_file"

printf 'EXPECTED_UID=%s\n' "$uid"
printf 'EXPECTED_GID=%s\n' "$gid"
printf 'EXPECTED_HOME=%s\n' "$home"

printf 'EXISTING_JOB_B64=%s\n' \
    "$(printf '%s' "$existing_line" | base64 -w0)"

printf 'MAINTENANCE_SHA256=%s\n' \
    "$(sha256sum /usr/local/sbin/cyberrange-maintenance | awk '{print $1}')"

printf 'WEEKLY_HELPER_SHA256=%s\n' \
    "$(sha256sum /usr/local/sbin/cyberrange-weekly-audit | awk '{print $1}')"

printf 'CRONTAB_SHA256=%s\n' \
    "$(sha256sum /etc/crontab | awk '{print $1}')"

printf 'UNRELATED_CRON_SHA256=%s\n' \
    "$(sha256sum "$unrelated_file" | awk '{print $1}')"
