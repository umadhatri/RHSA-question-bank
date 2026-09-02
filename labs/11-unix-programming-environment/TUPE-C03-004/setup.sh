#!/usr/bin/env bash
set -euo pipefail

: "${TEST_TOKEN:?TEST_TOKEN is required}"
: "${COUNT_A:?COUNT_A is required}"
: "${COUNT_B:?COUNT_B is required}"

bin_dir="/workspace/student_bin_${TEST_TOKEN}"
input_a="/workspace/data_a_${TEST_TOKEN}.txt"
input_b="/workspace/data_b_${TEST_TOKEN}.txt"
probe="/workspace/command_probe_${TEST_TOKEN}.txt"
resolved="/workspace/resolved_command_${TEST_TOKEN}.txt"

rm -rf -- "$bin_dir"
rm -f -- "$input_a" "$input_b" "$probe" "$resolved"

: > "$input_a"
for ((i = 1; i <= COUNT_A; i++)); do
    printf 'alpha-%s-%02d\n' "$TEST_TOKEN" "$i" >> "$input_a"
done

: > "$input_b"
for ((i = 1; i <= COUNT_B; i++)); do
    printf 'beta-%s-%02d\n' "$TEST_TOKEN" "$i" >> "$input_b"
done

# A decoy command later in PATH makes failure to create/enable the student's
# command observable without causing an infrastructure error.
cat > /usr/local/bin/recordcount <<'DECOY'
#!/usr/bin/env bash
printf '9999\n'
DECOY

chmod 0755 /usr/local/bin/recordcount
