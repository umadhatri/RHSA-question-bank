#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${TEST_VERSION:-}" ]]; then
    echo "TEST_VERSION is required" >&2
    exit 1
fi

version="1.${TEST_VERSION}.0"

topdir="/tmp/cyberrange-rpmbuild"
package_dir="/opt/cyberrange/packages"

mkdir -p \
    "$topdir"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS} \
    "$package_dir"

cat > "$topdir/SOURCES/cyberrange-monitor" <<'EOF'
#!/usr/bin/env bash
printf 'cyberrange-monitor-ok\n'
EOF

chmod 0755 "$topdir/SOURCES/cyberrange-monitor"

cat > "$topdir/SOURCES/cyberrange-monitor.conf" <<'EOF'
enabled=true
interval=30
EOF

chmod 0644 "$topdir/SOURCES/cyberrange-monitor.conf"

cat > "$topdir/SPECS/cyberrange-monitor.spec" <<EOF
Name:           cyberrange-monitor
Version:        ${version}
Release:        1
Summary:        CyberRange monitoring utility
License:        MIT
BuildArch:      noarch

Source0:        cyberrange-monitor
Source1:        cyberrange-monitor.conf

%description
Local package used for CyberRange package-management training.

%install
install -D -m 0755 \
    %{SOURCE0} \
    %{buildroot}/usr/local/bin/cyberrange-monitor

install -D -m 0644 \
    %{SOURCE1} \
    %{buildroot}/etc/cyberrange-monitor.conf

%files
/usr/local/bin/cyberrange-monitor
/etc/cyberrange-monitor.conf
EOF

rpmbuild \
    --define "_topdir $topdir" \
    -bb "$topdir/SPECS/cyberrange-monitor.spec" \
    >/dev/null

built_rpm="$(
    find "$topdir/RPMS" \
        -type f \
        -name 'cyberrange-monitor-*.rpm' \
        -print \
        -quit
)"

if [[ -z "$built_rpm" ]]; then
    echo "Failed to build test RPM" >&2
    exit 1
fi

install \
    -o root \
    -g root \
    -m 0644 \
    "$built_rpm" \
    "$package_dir/cyberrange-monitor.rpm"

printf 'EXPECTED_VERSION=%s\n' "$version"
printf 'EXPECTED_RELEASE=1\n'
printf 'EXPECTED_ARCH=noarch\n'

printf 'SOURCE_RPM_SHA256=%s\n' \
    "$(sha256sum "$package_dir/cyberrange-monitor.rpm" | awk '{print $1}')"

printf 'RPM_BINARY_SHA256=%s\n' \
    "$(sha256sum /usr/bin/rpm | awk '{print $1}')"

extract_root="/tmp/cyberrange-rpm-payload"

mkdir -p "$extract_root"

rpm \
    --root "$extract_root" \
    --dbpath /var/lib/rpm \
    --nodeps \
    --noscripts \
    --notriggers \
    -i "$package_dir/cyberrange-monitor.rpm"

printf 'EXECUTABLE_SHA256=%s\n' \
    "$(sha256sum "$extract_root/usr/local/bin/cyberrange-monitor" | awk '{print $1}')"

printf 'CONFIG_SHA256=%s\n' \
    "$(sha256sum "$extract_root/etc/cyberrange-monitor.conf" | awk '{print $1}')"

rm -rf "$extract_root"
