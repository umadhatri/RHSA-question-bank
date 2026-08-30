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

install -d -o root -g root -m 0755 /usr/local/sbin

cat > /usr/local/sbin/cyberrange-maintenance <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

if [[ "$(id -u)" -ne 0 ]]; then
    echo "This maintenance command must run as root." >&2
    exit 1
fi

printf 'maintenance-ok\n'
EOF

chown root:root /usr/local/sbin/cyberrange-maintenance
chmod 0755 /usr/local/sbin/cyberrange-maintenance

printf 'SUDOERS_SHA256=%s\n' \
    "$(sha256sum /etc/sudoers | awk '{print $1}')"

printf 'HELPER_SHA256=%s\n' \
    "$(sha256sum /usr/local/sbin/cyberrange-maintenance | awk '{print $1}')"

printf 'SUDO_BINARY_SHA256=%s\n' \
    "$(sha256sum /usr/bin/sudo | awk '{print $1}')"

printf 'VISUDO_BINARY_SHA256=%s\n' \
    "$(sha256sum /usr/sbin/visudo | awk '{print $1}')"
