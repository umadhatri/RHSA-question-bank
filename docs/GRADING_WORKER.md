# Grading Worker v0.1

The grading worker packages the private Linux sysadmin question bank into a trusted runtime that can launch disposable student sandboxes through Docker.

## Security boundary

There are three distinct images:

1. `cyberrange/rhsa-workspace:0.1` — interactive student terminal.
2. `cyberrange/rhsa-base:0.3` — disposable environment where untrusted student Bash is executed.
3. `cyberrange/rhsa-grading-worker:0.4.0` — trusted orchestration and hidden graders.

The worker contains `grader.py` files. The student sandbox does not. `grader/runner.py` copies only trusted `setup.sh` temporarily and the student's submission into the sandbox, exports filesystem snapshots after execution, then performs hidden grading outside that sandbox.

For the local proof of concept the worker receives `/var/run/docker.sock`. A Docker socket grants host-level control to the process holding it. **Never mount the production backend host's Docker socket into this worker.** Production workers must run only on dedicated grading capacity whose compromise does not expose the CyberRange application host.

## Build

```bash
./scripts/build-base.sh
./scripts/build-worker.sh
```

This produces:

```text
cyberrange/rhsa-grading-worker:0.4.0
cyberrange/rhsa-grading-worker:<git-revision>
```

The revision tag is intended to make grading attempts reproducible.

## Local worker smoke test

```bash
./scripts/smoke-worker.sh
```

The smoke test verifies:

- hidden graders exist in the trusted worker;
- instructor reference solutions are absent from the worker runtime;
- the untrusted `rhsa-base` image does not contain the question bank;
- the known-good `RHSA-USERS-001` submission scores `100/100`;
- the intentionally broken submission scores `60/100`;
- academic FAIL still exits successfully at the worker-job layer because the infrastructure completed correctly.

If Docker uses a nonstandard socket path:

```bash
DOCKER_SOCKET=/path/to/docker.sock ./scripts/smoke-worker.sh
```

## Worker contract

The worker entry point accepts:

```text
--lab-id       declared lab id, e.g. RHSA-USERS-001
--submission   path to the submitted Bash file
--result       destination for structured result JSON
--seed         optional deterministic grading seed
```

`grader/runner.py` exit codes are normalized by the worker:

- runner `0` (academic PASS) -> worker `0`
- runner `2` (academic FAIL) -> worker `0`
- runner `1` / missing result (infrastructure failure) -> worker `1`

This is deliberate: ECS should treat a student's failing solution as a completed grading job, not a failed task.

## Production direction

The local filesystem input/output transport is only for validating the worker image. The production executor should use an immutable submission object (for example S3), launch this image on dedicated ECS grading capacity, and retrieve the result object after completion. The CyberRange backend itself must never execute student Bash or mount a Docker socket.
