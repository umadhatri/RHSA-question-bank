# Workshop trainer guide

The authoritative exercise sequence and source mapping are in
`workshop.course.yaml`. Each workshop lab has a private `reference/solution.sh`.
Do not publish reference folders or graders to the participant workspace.

Use the proposal's morning teaching blocks. In practical time, Foundation gets
outcomes and structured guidance; Practitioner gets fewer procedural hints;
Advanced gets a scenario, asset register, constraints, and deliverables.

Before giving a hint ask what the participant inspected, expected, observed,
and hypothesized, and what evidence would disprove that hypothesis.

## Advanced hints and debrief

1. Service failure: first inspect controller/logs/processes; next compare command
   resolution with the approved executable location; finally check effective
   access as the service account. The fixes are PATH and input group/mode. A
   copied report file alone does not prove a running service. The local worker
   deliberately avoids systemd/network dependencies.
2. Persistence: compare SSH key comments to the asset register, inspect cron and
   sudo drop-ins, then correlate the synthetic authentication events. Preserve
   the approved key, maintenance job, scoped rule, logs, and account identities.
   Removing all keys or all cron configuration fails preservation checks.
3. Capstone: combine evidence collection, targeted removal, least privilege,
   service recovery, and repeatability. Ask the student to distinguish observed
   login evidence from assumptions about initial access and attacker intent.

A stopped controller may retain a stale PID file after experimentation. Inspect
that PID before removing the stale file and retrying the supplied controller.
Stopping/starting a CyberRange workspace rebuilds practice state, so keep copies
of scripts before resets. A grading attempt always starts fresh regardless of
interactive edits. Practice fixtures are fixed for demonstrations; core grading
uses randomized values and students must honor each question's argument contract.

Record attendance on both days, passed core exercises (majority = at least 5/9),
and at least one accepted capstone attempt. Apply the proposed pilot completion
rule manually; do not confuse the platform's full-module completion flag with
workshop attendance or certification. Record Foundation (3), Practitioner (6),
Advanced (3), capstone score, attempts, support requests, infrastructure incidents,
and time on task. Do not invent a stricter certificate threshold before the pilot.

The stretch list in the manifest references existing Linux exercises, requiring
separate Linux catalog access. Prepare Puzzle System Hardening as an optional
online fallback, and printed evidence for a platform outage.
