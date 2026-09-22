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

def inspect(snapshot, context, scenario):
    hashes = baseline(context)
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
    persistence = not snapshot.exists("/etc/cron.d/workshop-beacon") and not snapshot.exists("/etc/sudoers.d/workshop-override")
    try:
        answer = json.loads(snapshot.read_text("/workspace/findings.json") or "{}")
    except (ValueError, TypeError):
        answer = {}
    if not isinstance(answer, dict): answer = {}
    if scenario == 1:
        findings = answer.get("root_causes") == ["invalid_path", "input_permissions"]
    else:
        findings = answer.get("affected_account") == "wsoperator" and answer.get("source_ip") == "192.0.2.44" and set(answer.get("persistence", []) if isinstance(answer.get("persistence"), list) and all(isinstance(x,str) for x in answer["persistence"]) else []) == {"ssh_key", "cron", "sudo_override"}
        if scenario == 3:
            findings = findings and answer.get("root_causes") == ["invalid_path", "input_permissions"]
    return dict(service=service, configuration=config, legitimate_state=preserved, authorized_access=access, persistence_removed=persistence, findings=findings)

def grade(lab, context, snapshots):
    book = GradeBook(lab)
    scenario = int(lab["id"].rsplit("-", 1)[1])
    first = inspect(snapshots["after_first"], context, scenario)
    second = inspect(snapshots["after_second"], context, scenario)
    keys = [c["id"] for c in lab["grading"]["criteria"] if c["id"] not in {"execution", "idempotency"}]
    ran = all(context.get(k, {}).get("returncode", 1) == 0 and not context.get(k, {}).get("timed_out", False) for k in ("first_run", "second_run"))
    book.check("execution", bool(context.get("syntax_ok")) and ran, "Both executions succeeded.", "Syntax or execution failed.")
    for key in keys:
        book.check(key, first[key], key.replace("_", " ") + " verified.", key.replace("_", " ") + " is incomplete.")
    book.check("idempotency", ran and all(first[k] and second[k] for k in keys), "Required state survives repeated execution.", "Required state is not stable across both runs.")
    return book.finalize()
