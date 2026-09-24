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
ssh-keygen -q -t ed25519 -N '' -C approved-breakglass -f /tmp/breakglass-key
cat /tmp/breakglass-key.pub >> /home/wsoperator/.ssh/authorized_keys
rm /tmp/breakglass-key /tmp/breakglass-key.pub
chown wsoperator:wsoperator /home/wsoperator/.ssh/authorized_keys
chmod 0600 /home/wsoperator/.ssh/authorized_keys
cat > /workspace/asset-register.txt <<'EOF'
Approved accounts: wsoperator (administrator), reportsvc (non-login report service).
Approved keys: approved-admin, approved-breakglass. Approved schedule: workshop-maintenance.
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

case_number=$(od -An -N1 -tu1 /dev/urandom | tr -d ' ')
if (( case_number % 2 )); then
  case_id=EMBER-47
  source_ip=192.0.2.44
  rogue_comment=unapproved-remote-ember
  sudo_path=/etc/sudoers.d/workshop-override-ember
  cron_path=/etc/cron.d/workshop-beacon-ember
else
  case_id=SLATE-82
  source_ip=198.51.100.71
  rogue_comment=unapproved-remote-slate
  sudo_path=/etc/sudoers.d/ops-debug-slate
  cron_path=/etc/cron.d/logrotate-slate
fi
ssh-keygen -q -t ed25519 -N '' -C "$rogue_comment" -f /tmp/rogue-key
cat /tmp/rogue-key.pub >> /home/wsoperator/.ssh/authorized_keys
rm /tmp/rogue-key /tmp/rogue-key.pub
printf 'wsoperator ALL=(ALL) NOPASSWD: ALL\n' > "$sudo_path"
chmod 0666 "$sudo_path"
printf '* * * * * root /usr/bin/true # unauthorized beacon simulation\n' > "$cron_path"
cat > /workspace/incident-brief.txt <<EOF
SOC case: $case_id
Host: report server
Reported symptoms: unusual privileged activity and intermittent report-service failure.
Responder objective: establish an evidence-backed timeline, contain unauthorized access, preserve approved state, and recover the service.
EOF
printf 'Sep 21 09:12:08 host sshd[812]: Accepted publickey for wsoperator from %s port 50123 ssh2: %s\nSep 21 09:13:20 host sshd[819]: Accepted publickey for wsoperator from 203.0.113.9 port 48002 ssh2: approved-breakglass\nSep 21 09:16:01 host sudo: wsoperator : COMMAND=/usr/bin/tee %s\nSep 21 09:16:32 host sudo: wsoperator : COMMAND=/usr/bin/tee %s\n' "$source_ip" "$rogue_comment" "$cron_path" "$sudo_path" > /var/log/workshop/auth.log
printf 'BASELINE /var/log/workshop/auth.log %s\n' "$(sha256sum /var/log/workshop/auth.log | cut -d' ' -f1)"
printf 'CAPSTONE_CASE %s %s %s %s %s\n' "$case_id" "$source_ip" "$rogue_comment" "$cron_path" "$sudo_path"

printf 'PATH=/missing/workshop/bin\n' > /etc/workshop/service.env
chown root:root /srv/workshop/input.txt
chmod 0600 /srv/workshop/input.txt
printf 'Service unavailable after maintenance. Investigate environment and access with evidence.\n' > /var/log/workshop/service.log
