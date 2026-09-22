# WS-CORE-008 — Failed SSH Login Analyzer

Write a Bash script named `analyze_auth.sh` that accepts:

```text
analyze_auth.sh AUTH_LOG OUTPUT_FILE
```

The input is a Linux-style SSH authentication log containing successful logins, failed logins, and unrelated messages.

Your script must:

- Count **only** lines containing the SSH phrase `Failed password`.
- Extract the source IPv4 address from each matching line.
- Write one line per source IP to `OUTPUT_FILE` using exactly this format:

```text
COUNT IP_ADDRESS
```

- Sort the report by count in descending numeric order. If counts are equal, sort by IP address in ascending lexical order.
- Do not include successful logins or unrelated messages.
- Do not emit duplicate IP rows.
- Overwrite the report rather than append to it, so running the script repeatedly produces the same correct report.

The log filename, output filename, IP addresses, and event counts vary between grading attempts. Do not hard-code them.


## Workshop context
Day 2 · Practitioner · 14:40-15:10. Adapted from RHSA-TEXT-001.
Inspect, make a hypothesis, change the required state, and verify it before submitting.
