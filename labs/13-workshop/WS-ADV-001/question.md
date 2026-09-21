# Advanced Service Failure Investigation

The business team reports an unavailable report service. Investigate the host, identify the causes, and restore secure operation while preserving legitimate access, jobs, data, logs, and service code.

Read `/workspace/asset-register.txt` for the approved baseline. Inspect actual state against that baseline; do not assume every unfamiliar artifact is unauthorized. The service is a local background report worker, not a systemd or network service. It must run as `reportsvc` and produce the approved business output. Use its supplied service controller to start it after repairing the causes.

Submit `remediate.sh`. The platform reruns your script twice in a fresh isolated environment: include all fixes and creation of `/workspace/findings.json` in the script. Interactive changes alone are not submitted. Preserve evidence before remediation and explain your investigation during the debrief.

Findings JSON fields: `root_causes`: ordered codes for the environment fault then the data-access fault.

Use these vocabulary codes where supported by the evidence: `invalid_path`, `input_permissions`, `ssh_key`, `cron`, `sudo_override`. Not every field applies to every scenario. Findings are scored alongside actual system state; answers alone do not restore the host.

Constraints: preserve approved accounts and their identities, approved SSH key, approved maintenance and scoped sudo rule, original business input, and original service executables. Keep input `root:reportsvc` with mode `0640`, environment `root:root` with mode `0644`, and SSH directory/key modes `0700`/`0600`. Remove only unauthorized persistence. Broad permission changes or deleting all access/job configuration will lose preservation marks.
