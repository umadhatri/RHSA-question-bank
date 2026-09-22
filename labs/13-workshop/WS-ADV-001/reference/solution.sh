#!/usr/bin/env bash
set -euo pipefail
printf 'PATH=/opt/workshop/bin:/usr/bin:/bin\n' > /etc/workshop/service.env
chown root:root /etc/workshop/service.env
chmod 0644 /etc/workshop/service.env
chown root:reportsvc /srv/workshop/input.txt
chmod 0640 /srv/workshop/input.txt
#!/usr/bin/env bash
set -euo pipefail
printf 'PATH=/opt/workshop/bin:/usr/bin:/bin\n' > /etc/workshop/service.env
chown root:root /etc/workshop/service.env
chmod 0644 /etc/workshop/service.env
chown root:reportsvc /srv/workshop/input.txt
chmod 0640 /srv/workshop/input.txt
/usr/local/sbin/workshop-service start
cat > /workspace/findings.json <<'EOF'
{
  "root_causes": [
    "invalid_path",
    "input_permissions"
  ]
}
EOF
