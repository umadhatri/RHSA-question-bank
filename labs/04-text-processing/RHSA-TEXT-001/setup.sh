#!/usr/bin/env bash
set -euo pipefail
: "${TEST_TOKEN:?}" "${IP_A:?}" "${IP_B:?}" "${IP_C:?}" "${COUNT_A:?}" "${COUNT_B:?}" "${COUNT_C:?}"

mkdir -p /var/log/training
log="/var/log/training/auth_${TEST_TOKEN}.log"
: > "$log"

printf 'Aug 25 09:00:00 host sshd[100]: Accepted password for admin from 198.51.100.22 port 5000 ssh2\n' >> "$log"
printf 'Aug 25 09:00:01 host systemd[1]: Started Session 42 of User root.\n' >> "$log"

for ((i=0; i<COUNT_B; i++)); do
  printf 'Aug 25 09:01:%02d host sshd[%d]: Failed password for invalid user guest from %s port %d ssh2\n' "$i" "$((200+i))" "$IP_B" "$((4100+i))" >> "$log"
done
for ((i=0; i<COUNT_A; i++)); do
  printf 'Aug 25 09:02:%02d host sshd[%d]: Failed password for root from %s port %d ssh2\n' "$i" "$((300+i))" "$IP_A" "$((4200+i))" >> "$log"
done
printf 'Aug 25 09:03:00 host sshd[400]: Accepted publickey for student from %s port 4300 ssh2\n' "$IP_A" >> "$log"
for ((i=0; i<COUNT_C; i++)); do
  printf 'Aug 25 09:04:%02d host sshd[%d]: Failed password for invalid user oracle from %s port %d ssh2\n' "$i" "$((500+i))" "$IP_C" "$((4400+i))" >> "$log"
done
printf 'Aug 25 09:05:00 host kernel: firewall: Failed checksum from 192.0.2.5\n' >> "$log"
