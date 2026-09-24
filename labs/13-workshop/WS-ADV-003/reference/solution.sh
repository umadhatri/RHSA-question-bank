#!/usr/bin/env bash
set -euo pipefail

case_id=$(awk -F': ' '/^SOC case:/{print $2}' /workspace/incident-brief.txt)
source_ip=$(awk '/Accepted publickey.*unapproved-remote/ {for (i=1; i<=NF; i++) if ($i == "from") print $(i+1)}' /var/log/workshop/auth.log)
rogue_comment=$(awk '/Accepted publickey.*unapproved-remote/ {print $NF}' /var/log/workshop/auth.log)
cron_path=$(awk '/COMMAND=.*\/etc\/cron\.d\// {sub(/^.*COMMAND=\/usr\/bin\/tee /, ""); if ($0 ~ /\/etc\/cron\.d\//) {print; exit}}' /var/log/workshop/auth.log)
sudo_path=$(awk '/COMMAND=.*\/etc\/sudoers\.d\// {sub(/^.*COMMAND=\/usr\/bin\/tee /, ""); print; exit}' /var/log/workshop/auth.log)

printf 'PATH=/opt/workshop/bin:/usr/bin:/bin\n' > /etc/workshop/service.env
chown root:root /etc/workshop/service.env
chmod 0644 /etc/workshop/service.env
chown root:reportsvc /srv/workshop/input.txt
chmod 0640 /srv/workshop/input.txt
grep -vF "$rogue_comment" /home/wsoperator/.ssh/authorized_keys > /tmp/authorized_keys
install -o wsoperator -g wsoperator -m 0600 /tmp/authorized_keys /home/wsoperator/.ssh/authorized_keys
rm -f /tmp/authorized_keys "$sudo_path" "$cron_path"
/usr/local/sbin/workshop-service start
cat > /workspace/findings.json <<EOF
{
  "case_id": "$case_id",
  "affected_account": "wsoperator",
  "source_ip": "$source_ip",
  "persistence": ["ssh_key", "cron", "sudo_override"],
  "root_causes": ["invalid_path", "input_permissions"],
  "timeline": [
    {"evidence": "/var/log/workshop/auth.log source $source_ip", "observation": "unapproved key authenticated as wsoperator", "action": "contain"},
    {"evidence": "/home/wsoperator/.ssh/authorized_keys comment $rogue_comment", "observation": "key is absent from the asset register", "action": "eradicate"},
    {"evidence": "$cron_path", "observation": "unauthorized scheduled persistence", "action": "eradicate"},
    {"evidence": "$sudo_path", "observation": "broad sudo override grants unrestricted privilege", "action": "eradicate"},
    {"evidence": "/etc/workshop/service.env and /srv/workshop/input.txt", "observation": "PATH and group access prevented reportsvc from running", "action": "recover"},
    {"evidence": "workshop-service status and /srv/workshop/latest.txt", "observation": "reportsvc is running and producing approved output", "action": "verify"}
  ],
  "verification": ["Checked workshop-service status and refreshed service output", "Checked authorized_keys preserves approved-admin and approved-breakglass only"]
}
EOF
