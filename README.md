# CyberRange Linux Sysadmin Bash Autograder

A terminal-only, state-based autograder for Linux system-administration Bash labs. Students write scripts in the terminal; each submission runs in a fresh RHEL-compatible container; hidden Python graders inspect Linux state and award criterion-level marks.

The repository is designed to become the **private course question bank**. Adding a new lab should require new course content, not changes to the CyberRange backend.

## Contract v1

The stable question/grader interface is documented in `docs/GRADER_CONTRACT.md`.

Core guarantees:

- one disposable container per grading attempt;
- randomized hidden values to discourage hard-coded answers;
- state-based checks instead of regex matching;
- partial rubric scoring;
- two filesystem snapshots (`after_first`, `after_second`) for strong idempotency checking;
- hidden graders never copied into the student container;
- no network access in grading containers;
- CPU, memory, and PID limits;
- reproducibility metadata and structured result JSON;
- schema validation and CI checks for question authors.

## Repository layout

```text
linux-sysadmin-autograder/
├── course.yaml
├── grader/                  # generic engine; question authors normally do not edit
├── schemas/                 # lab + result contracts
├── docker/base/             # Rocky Linux base image
├── labs/                    # actual private question bank
├── templates/lab-template/  # copy when authoring a new question
├── tests/                   # contract + grader unit tests
├── scripts/
└── docs/GRADER_CONTRACT.md
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Build the base image:

```bash
./scripts/build-base.sh
```

## Validate the repository

No Docker required:

```bash
./scripts/test.sh
```

This should be run before every commit that adds or changes a lab.

## Run the reference lab

Correct submission:

```bash
python3 grader/runner.py \
  --lab labs/01-users-groups/RHSA-USERS-001 \
  --submission examples/student_good.sh
```

Intentionally broken submission:

```bash
python3 grader/runner.py \
  --lab labs/01-users-groups/RHSA-USERS-001 \
  --submission examples/student_bad.sh
```

Full smoke test:

```bash
./scripts/smoke-test.sh
```

Write structured output for later FastAPI/CyberRange integration:

```bash
python3 grader/runner.py \
  --lab labs/01-users-groups/RHSA-USERS-001 \
  --submission examples/student_good.sh \
  --json-out result.json
```

## Current reference question

`RHSA-USERS-001 — User and Group Provisioning` is the canonical contract-v1 example. It checks users, groups, shell, membership, directory creation, group ownership, permissions, and strong idempotency.

A correct script should score 100/100. The intentionally broken sample should fail and, under contract v1, cannot receive idempotency points merely because its second execution exits successfully.

## Security note

This is a development runner for the grading model, not the final hostile-code isolation boundary. Production execution should move into dedicated CyberRange ECS grading tasks with no host mounts, Docker socket, AWS credentials, or unnecessary network access.
