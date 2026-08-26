# Grading Worker v0.2 / Image v0.4.1

The grading worker packages the private Linux sysadmin question bank into a trusted runtime that launches disposable student sandboxes through a Docker daemon on **dedicated grading capacity**.

## Security boundary

There are three distinct images:

1. `cyberrange/rhsa-workspace:0.1` — interactive student terminal.
2. `cyberrange/rhsa-base:0.3` — disposable environment where untrusted student Bash executes.
3. `cyberrange/rhsa-grading-worker:0.4.1` — trusted orchestration, hidden graders, remote job transport, and ECR pull support.

The worker contains private `grader.py` files. The student sandbox does not. `grader/runner.py` copies only trusted `setup.sh` temporarily and the student's submission into the sandbox, exports filesystem snapshots after execution, stops the sandbox, and performs hidden grading outside it.

The trusted worker needs Docker-daemon access. A Docker socket is effectively host-level control, so the worker must run only on dedicated grading hosts whose compromise cannot expose the CyberRange application host or ordinary student-lab capacity.

The untrusted sandbox is created with resource limits, `no-new-privileges`, and `--network none`. It receives no AWS credentials, S3 URLs, Docker socket, question bank, or hidden grader.

## Build

```bash
./scripts/build-base.sh
./scripts/build-worker.sh
```

This produces:

```text
cyberrange/rhsa-grading-worker:0.4.1
cyberrange/rhsa-grading-worker:<git-revision>
```

The Git-revision tag is intended for reproducible grading deployments.

## Local-path worker contract

Development/local smoke tests remain supported:

```text
--lab-id       declared lab id, e.g. RHSA-USERS-001
--submission   local path to submitted Bash
--result       local path for result JSON
--seed         optional deterministic grading seed
--base-image   optional Docker sandbox image override
```

`grader/runner.py` exit codes are normalized by the worker:

- runner `0` (academic PASS) -> worker `0`
- runner `2` (academic FAIL) -> worker `0`
- runner `1` / missing result (infrastructure failure) -> worker `1`

This is deliberate: ECS must treat a student's failing solution as a completed grading job, not a failed task.

## Remote ECS job contract

v0.4.1 adds an object-transport mode intended for short-lived presigned object URLs:

```text
--submission-url   HTTP(S) GET URL for immutable submission.sh
--result-url       HTTP(S) PUT URL for result.json
--base-image       production sandbox image, normally an ECR URI
--pull-base-image  authenticate/pull the sandbox image before grading
```

All job fields can also be provided through environment variables, which is convenient for ECS task overrides:

```text
RHSA_LAB_ID
RHSA_SEED
RHSA_SUBMISSION_URL
RHSA_RESULT_URL
RHSA_BASE_IMAGE
RHSA_PULL_BASE_IMAGE=true
RHSA_MAX_SUBMISSION_BYTES=65536
RHSA_HTTP_TIMEOUT_SECONDS=30
```

The worker never logs the submission or result URL because presigned URLs are bearer secrets until they expire.

A typical production job looks like:

```text
RHSA_LAB_ID=RHSA-USERS-001
RHSA_SEED=424242
RHSA_SUBMISSION_URL=<short-lived presigned GET>
RHSA_RESULT_URL=<short-lived presigned PUT>
RHSA_BASE_IMAGE=766363046973.dkr.ecr.ap-south-1.amazonaws.com/cyberrange/rhsa-base:0.3
RHSA_PULL_BASE_IMAGE=true
```

The worker downloads the submission into its private temporary directory, authenticates Docker to ECR when the image is an ECR URI, pulls the sandbox image, invokes the existing generic runner with `--image-override`, and PUTs the resulting JSON to the result URL.

### ECR permissions

For private ECR sandbox pulls, the **worker ECS task role** should be narrowly scoped to ECR pull operations. It needs `ecr:GetAuthorizationToken` plus repository pull actions such as `ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, and `ecr:BatchGetImage` for the sandbox repository.

The worker image contains AWS CLI only so the trusted worker can obtain the short-lived ECR Docker authorization token from its ECS task role. The student sandbox never receives that role or token.

## Submission transport constraints

The remote worker accepts only absolute `http://` or `https://` URLs. The default maximum submission size is 64 KiB. Empty or oversized downloads are rejected before student code executes.

The result is uploaded with HTTP PUT and `Content-Type: application/json`. Production presigned PUT generation should use matching semantics.

## Smoke tests

Local-path isolation and academic-result behavior:

```bash
./scripts/smoke-worker.sh
```

Remote object-transport behavior:

```bash
./scripts/smoke-worker-remote.sh
```

The remote smoke test creates a temporary Docker network and a tiny mock object store, downloads both canonical submissions over HTTP, grades them through the trusted worker, uploads their results over HTTP, and verifies `100/100 PASS` and `60/100 FAIL`. The student sandbox still runs with no network.

If Docker uses a nonstandard socket:

```bash
DOCKER_SOCKET=/path/to/docker.sock ./scripts/smoke-worker.sh
DOCKER_SOCKET=/path/to/docker.sock ./scripts/smoke-worker-remote.sh
```

## Production boundary

The trusted worker may have:

- Docker socket access on its dedicated grading host;
- network access needed for presigned object URLs and ECR;
- a narrowly scoped ECS task role for ECR pull authentication.

The untrusted student sandbox must have:

- no Docker socket;
- no AWS/task credentials;
- no question bank or hidden grader;
- no unnecessary host mounts;
- no network;
- strict CPU, memory, PID, and execution-time limits.

Do not run this trusted worker on the CyberRange application EC2 instance.
