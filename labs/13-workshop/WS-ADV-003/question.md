# Compromised Linux Service - Investigate, Contain, Recover

You are the on-call responder for a report server. The SOC case brief is in
`/workspace/incident-brief.txt`. It reports suspicious privileged activity and
intermittent failure of the reporting service.

Investigate the live host. Determine the evidence-backed access path, identify
unauthorized persistence, restore secure operation, and preserve every approved
account, key, job, rule, data file, log, and service executable. The asset register
is a baseline, not an answer key: an unfamiliar-looking artifact is not automatically
malicious.

The service is a local background report worker, not a systemd or network service.
It must run as `reportsvc` and continually produce the approved business output. Use
the supplied controller only after repairing the causes you identify.

## Deliverables

Submit `remediate.sh`. The platform reruns it twice from a fresh isolated state, so
it must contain every remediation and create `/workspace/findings.json`. Interactive
changes alone are not submitted.

Your findings file must be valid JSON with this shape:

```json
{
  "case_id": "value from incident-brief.txt",
  "affected_account": "account supported by evidence",
  "source_ip": "source supported by evidence",
  "persistence": ["ssh_key", "cron", "sudo_override"],
  "root_causes": ["invalid_path", "input_permissions"],
  "timeline": [
    {"evidence": "log or host artifact", "observation": "what it proves", "action": "contain, eradicate, recover, or verify"}
  ],
  "verification": ["specific secure or operational check", "another check"]
}
```

`persistence` and `root_causes` use only the codes supported by evidence. The
timeline must contain at least four ordered entries that connect evidence to a
decision; copied generic incident-response text will not satisfy the assessment.

## Constraints

Preserve approved accounts and identities, approved SSH keys, approved scheduled
jobs and scoped sudo rules, original business input, service executables, and logs.
Keep input `root:reportsvc` with mode `0640`, environment `root:root` with mode
`0644`, and SSH directory/key modes `0700`/`0600`. Remove only unauthorized
persistence. Broad permission changes or deleting all access/job configuration lose
preservation marks.
