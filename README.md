# CyberRange Linux Sysadmin Bash Autograder

A terminal-only, state-based autograder and private question bank for Linux system-administration Bash labs. Students write scripts in the terminal; each grading attempt runs in a fresh RHEL-compatible container; hidden Python graders inspect the resulting Linux state or generated artifacts and award criterion-level marks.

## Question bank v0.3

The bank currently contains five labs:

- `RHSA-SHELL-001` — File Organizer
- `RHSA-FILE-001` — Secure Shared Project Directory
- `RHSA-USERS-001` — User and Group Provisioning
- `RHSA-TEXT-001` — Failed SSH Login Analyzer
- `RHSA-BACKUP-001` — Automated Compressed Backup

See `docs/QUESTION_BANK.md` for the module map and skills covered.

## Contract v1

The stable question/grader interface is documented in `docs/GRADER_CONTRACT.md`.

Core guarantees:

- one disposable container per grading attempt;
- seed-reproducible hidden values to discourage hard-coded answers;
- state/artifact-based checks instead of regex command matching;
- partial rubric scoring;
- two filesystem snapshots (`after_first`, `after_second`) for strong idempotency checking;
- hidden graders never copied into the student container;
- no network access in grading containers;
- CPU, memory, and PID limits;
- reproducibility metadata and structured result JSON;
- schema validation, grader unit tests, and CI checks for question authors.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Validate the repository without Docker:

```bash
./scripts/test.sh
```

Build the Rocky Linux grading image:

```bash
./scripts/build-base.sh
```

Run every reference solution end-to-end plus the canonical broken sample:

```bash
./scripts/smoke-test.sh
```

Run one lab directly:

```bash
python3 grader/runner.py \
  --lab labs/01-shell-basics/RHSA-SHELL-001 \
  --submission labs/01-shell-basics/RHSA-SHELL-001/reference/solution.sh \
  --seed 424242
```

To write a structured result for later FastAPI/CyberRange integration:

```bash
python3 grader/runner.py \
  --lab labs/03-users-groups/RHSA-USERS-001 \
  --submission examples/student_good.sh \
  --seed 424242 \
  --json-out result.json
```

## Trusted grading worker

The question bank also builds a trusted worker image that preserves the hidden-grader isolation model when grading is moved off a developer machine:

```bash
./scripts/build-worker.sh
./scripts/smoke-worker.sh
```

The worker image is `cyberrange/rhsa-grading-worker:0.4.0`. It contains the private graders and launches the existing `cyberrange/rhsa-base:0.3` image as the untrusted student sandbox. See `docs/GRADING_WORKER.md` for the security boundary and production constraints.

## Repository layout

```text
linux-sysadmin-autograder/
├── course.yaml
├── grader/                  # generic engine
├── schemas/                 # lab + result contracts
├── docker/base/             # Rocky Linux base image
├── labs/                    # private question bank
├── templates/lab-template/  # starting point for new questions
├── tests/                   # contract + hidden-grader unit tests
├── scripts/
└── docs/
```

## Security note

The standalone Docker runner is the development implementation of the grading model, not the final hostile-code isolation boundary. Production execution should move into dedicated CyberRange ECS grading tasks with no host mounts, Docker socket, AWS credentials, or unnecessary network access.
