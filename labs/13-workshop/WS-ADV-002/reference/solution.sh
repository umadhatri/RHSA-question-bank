#!/usr/bin/env bash
set -euo pipefail
printf 'PATH=/opt/workshop/bin:/usr/bin:/bin\n' > /etc/workshop/service.env
chown root:root /etc/workshop/service.env
chmod 0644 /etc/workshop/service.env
chown root:reportsvc /srv/workshop/input.txt
chmod 0640 /srv/workshop/input.txt
sed -i '/unapproved-remote$/d' /home/wsoperator/.ssh/authorized_keys
chown wsoperator:wsoperator /home/wsoperator/.ssh/authorized_keys
chmod 0600 /home/wsoperator/.ssh/authorized_keys
rm -f /etc/sudoers.d/workshop-override /etc/cron.d/workshop-beacon
#!/usr/bin/env bash
set -euo pipefail
printf 'PATH=/opt/workshop/bin:/usr/bin:/bin\n' > /etc/workshop/service.env
chown root:root /etc/workshop/service.env
chmod 0644 /etc/workshop/service.env
chown root:reportsvc /srv/workshop/input.txt
chmod 0640 /srv/workshop/input.txt
sed -i '/unapproved-remote$/d' /home/wsoperator/.ssh/authorized_keys
chown wsoperator:wsoperator /home/wsoperator/.ssh/authorized_keys
chmod 0600 /home/wsoperator/.ssh/authorized_keys
rm -f /etc/sudoers.d/workshop-override /etc/cron.d/workshop-beacon
/usr/local/sbin/workshop-service start
cat > /workspace/findings.json <<'EOF'
{
  "affected_account": "wsoperator",
  "source_ip": "192.0.2.44",
  "persistence": [
    "ssh_key",
    "cron",
    "sudo_override"
  ]
}
EOF
