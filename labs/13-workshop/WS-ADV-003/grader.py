from __future__ import annotations
import hashlib
import json
from grader.api import GradeBook

def baseline(context):
    result = {}
    for line in context.get("setup", {}).get("stdout", "").splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[0] == "BASELINE":
            result[parts[1]] = parts[2]
    return result

def case_details(context):
    for line in context.get("setup", {}).get("stdout", "").splitlines():
        parts = line.split()
        if len(parts) == 6 and parts[0] == "CAPSTONE_CASE":
            return dict(case_id=parts[1], source_ip=parts[2], rogue_comment=parts[3], cron_path=parts[4], sudo_path=parts[5])
    return {}

def inspect(snapshot, context):
    hashes = baseline(context)
    case = case_details(context)
    def unchanged(path):
        raw = snapshot.read_bytes(path)
        return raw is not None and path in hashes and hashlib.sha256(raw).hexdigest() == hashes[path]
    preserved = all(unchanged(p) for p in hashes if p != "/home/wsoperator/.ssh/authorized_keys")
    preserved = preserved and all(snapshot.uid(p) == 0 and snapshot.mode(p) == mode for p, mode in {
        "/opt/workshop/bin/report-job": 0o755,
        "/usr/local/sbin/workshop-service": 0o755,
        "/etc/cron.d/workshop-maintenance": 0o644,
        "/etc/sudoers.d/workshop-wsoperator": 0o440,
    }.items())
    user = snapshot.user("reportsvc")
    processes = (snapshot.read_text("/run/workshop-processes") or "").splitlines()
    service = bool(user and len(processes) == 1 and len(processes[0].split()) == 2 and processes[0].split()[1] == str(user.uid))
    service = service and snapshot.read_bytes("/srv/workshop/latest.txt") == b"approved-business-data\n"
    config = snapshot.read_text("/etc/workshop/service.env") == "PATH=/opt/workshop/bin:/usr/bin:/bin\n"
    config = config and snapshot.uid("/srv/workshop/input.txt") == 0 and snapshot.gid("/srv/workshop/input.txt") == (user.gid if user else -1) and snapshot.mode("/srv/workshop/input.txt") == 0o640
    config = config and snapshot.uid("/etc/workshop/service.env") == 0 and snapshot.mode("/etc/workshop/service.env") == 0o644
    wsoperator = snapshot.user("wsoperator")
    access = unchanged("/home/wsoperator/.ssh/authorized_keys") and bool(wsoperator)
    access = access and snapshot.uid("/home/wsoperator/.ssh/authorized_keys") == (wsoperator.uid if wsoperator else -1) and snapshot.mode("/home/wsoperator/.ssh/authorized_keys") == 0o600
    access = access and snapshot.mode("/home/wsoperator/.ssh") == 0o700
    persistence = bool(case) and not snapshot.exists(case["cron_path"]) and not snapshot.exists(case["sudo_path"])
    try:
        answer = json.loads(snapshot.read_text("/workspace/findings.json") or "{}")
    except (ValueError, TypeError):
        answer = {}
    if not isinstance(answer, dict):
        answer = {}
    timeline = answer.get("timeline")
    verification = answer.get("verification")
    timeline_valid = isinstance(timeline, list) and len(timeline) >= 4 and all(
        isinstance(item, dict) and all(isinstance(item.get(key), str) and item[key].strip() for key in ("evidence", "observation", "action"))
        for item in timeline
    )
    if timeline_valid:
        evidence = "\n".join(item["evidence"] for item in timeline).lower()
        actions = {item["action"].strip().lower() for item in timeline}
        timeline_valid = actions >= {"contain", "eradicate", "recover", "verify"}
        timeline_valid = timeline_valid and all(token.lower() in evidence for token in (
            case.get("source_ip", ""), case.get("rogue_comment", ""), case.get("cron_path", ""), case.get("sudo_path", "")
        ))
    verification_valid = isinstance(verification, list) and len(verification) >= 2 and all(isinstance(item, str) and item.strip() for item in verification)
    if verification_valid:
        verification_text = "\n".join(verification).lower()
        verification_valid = "service" in verification_text and ("ssh" in verification_text or "authorized_keys" in verification_text)
    findings = bool(case) and answer.get("case_id") == case.get("case_id") and answer.get("affected_account") == "wsoperator"
    findings = findings and answer.get("source_ip") == case.get("source_ip")
    findings = findings and set(answer.get("persistence", []) if isinstance(answer.get("persistence"), list) and all(isinstance(x, str) for x in answer["persistence"]) else []) == {"ssh_key", "cron", "sudo_override"}
    findings = findings and answer.get("root_causes") == ["invalid_path", "input_permissions"] and timeline_valid and verification_valid
    return dict(service=service, configuration=config, legitimate_state=preserved, authorized_access=access, persistence_removed=persistence, findings=findings)

def grade(lab, context, snapshots):
    book = GradeBook(lab)
    first = inspect(snapshots["after_first"], context)
    second = inspect(snapshots["after_second"], context)
    keys = [c["id"] for c in lab["grading"]["criteria"] if c["id"] not in {"execution", "idempotency"}]
    ran = all(context.get(k, {}).get("returncode", 1) == 0 and not context.get(k, {}).get("timed_out", False) for k in ("first_run", "second_run"))
    book.check("execution", bool(context.get("syntax_ok")) and ran, "Both executions succeeded.", "Syntax or execution failed.")
    for key in keys:
        book.check(key, first[key], key.replace("_", " ") + " verified.", key.replace("_", " ") + " is incomplete.")
    book.check("idempotency", ran and all(first[k] and second[k] for k in keys), "Required state survives repeated execution.", "Required state is not stable across both runs.")
    return book.finalize()
