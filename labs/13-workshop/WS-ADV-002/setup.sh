#!/usr/bin/env bash
set -euo pipefail
useradd -m -s /bin/bash wsoperator
useradd -m -s /sbin/nologin reportsvc
install -d -m 0755 /etc/cron.d /etc/sudoers.d /opt/workshop/bin /etc/workshop /var/log/workshop /workspace
install -d -o reportsvc -g reportsvc -m 0750 /srv/workshop
printf 'approved-business-data\n' > /srv/workshop/input.txt
chown root:reportsvc /srv/workshop/input.txt
chmod 0640 /srv/workshop/input.txt
printf 'PATH=/opt/workshop/bin:/usr/bin:/bin\n' > /etc/workshop/service.env
cat > /opt/workshop/bin/report-job <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
while true; do
  cat /srv/workshop/input.txt > /srv/workshop/latest.txt
  sleep 1
done
EOF
cat > /usr/local/sbin/workshop-service <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
case "${1:-}" in
  start)
    if [[ -f /run/workshop-service.pid ]] && kill -0 "$(cat /run/workshop-service.pid)" 2>/dev/null; then exit 0; fi
    set -a
    source /etc/workshop/service.env
    set +a
    /usr/sbin/runuser -u reportsvc -- bash -c 'exec report-job' >> /var/log/workshop/service.log 2>&1 &
    echo $! > /run/workshop-service.pid
    ;;
  status) [[ -f /run/workshop-service.pid ]] && kill -0 "$(cat /run/workshop-service.pid)" ;;
  *) echo 'Usage: workshop-service start|status' >&2; exit 2 ;;
esac
EOF
chmod 0755 /opt/workshop/bin/report-job /usr/local/sbin/workshop-service
printf '15 2 * * * root /usr/bin/true # approved maintenance\n' > /etc/cron.d/workshop-maintenance
chmod 0644 /etc/cron.d/workshop-maintenance
printf 'wsoperator ALL=(root) /usr/bin/true\n' > /etc/sudoers.d/workshop-wsoperator
chmod 0440 /etc/sudoers.d/workshop-wsoperator
install -d -o wsoperator -g wsoperator -m 0700 /home/wsoperator/.ssh
ssh-keygen -q -t ed25519 -N '' -C approved-admin -f /tmp/approved-key
cat /tmp/approved-key.pub > /home/wsoperator/.ssh/authorized_keys
rm /tmp/approved-key /tmp/approved-key.pub
chown wsoperator:wsoperator /home/wsoperator/.ssh/authorized_keys
chmod 0600 /home/wsoperator/.ssh/authorized_keys
cat > /workspace/asset-register.txt <<'EOF'
Approved accounts: wsoperator (administrator), reportsvc (non-login report service).
Approved key: approved-admin. Approved schedule: workshop-maintenance.
Operator privilege: /usr/bin/true only. Service: workshop-service start|status.
Service environment: /etc/workshop/service.env; executable: /opt/workshop/bin/report-job.
Service data: /srv/workshop/input.txt (root:reportsvc 0640).
Expected output: /srv/workshop/latest.txt contains the business input, refreshed by reportsvc.
Preserve original business input, approved access, maintenance, service code, and logs.
EOF
# Record baseline evidence outside the student's eventual snapshot.
for path in /srv/workshop/input.txt /opt/workshop/bin/report-job /usr/local/sbin/workshop-service /etc/cron.d/workshop-maintenance /etc/sudoers.d/workshop-wsoperator /home/wsoperator/.ssh/authorized_keys /etc/passwd /etc/group; do
  printf 'BASELINE %s %s\n' "$path" "$(sha256sum "$path" | cut -d' ' -f1)"
done

ssh-keygen -q -t ed25519 -N '' -C unapproved-remote -f /tmp/rogue-key
cat /tmp/rogue-key.pub >> /home/wsoperator/.ssh/authorized_keys
rm /tmp/rogue-key /tmp/rogue-key.pub
printf 'wsoperator ALL=(ALL) NOPASSWD: ALL\n' > /etc/sudoers.d/workshop-override
chmod 0666 /etc/sudoers.d/workshop-override
printf '* * * * * root /usr/bin/true # unauthorized beacon simulation\n' > /etc/cron.d/workshop-beacon
printf 'Sep 21 09:14:02 host sshd[812]: Accepted publickey for wsoperator from 192.0.2.44 port 50123 ssh2: unapproved-remote\nSep 21 09:16:01 host sudo: wsoperator : COMMAND=/usr/bin/tee /etc/cron.d/workshop-beacon\n' > /var/log/workshop/auth.log
printf 'BASELINE /var/log/workshop/auth.log %s\n' "$(sha256sum /var/log/workshop/auth.log | cut -d' ' -f1)"
/usr/local/sbin/workshop-service start
sleep 1
