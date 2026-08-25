# Contributing Linux Sysadmin Lab Questions

This repository is the private instructor-side source of truth for Linux sysadmin Bash assignments and their hidden graders.

Before adding questions, read `docs/GRADER_CONTRACT.md`.

## Add a question

Start from `templates/lab-template/` and create one directory under the appropriate module. The directory name must exactly match the `id` in `lab.yaml`.

Every question requires:

- `question.md` — student-facing instructions;
- `lab.yaml` — contract-v1 execution, randomization, and rubric metadata;
- `setup.sh` — trusted deterministic initial-state setup;
- `grader.py` — hidden host-side checker with `grade(lab, context, snapshots)`.

Recommended:

- `reference/solution.sh` — instructor reference implementation;
- `fixtures/` — public or hidden input data needed by the setup.

## Before committing

Run:

```bash
./scripts/test.sh
```

This validates every lab manifest, rubric total, grader entry point, directory naming convention, and unit test. GitHub Actions runs the same checks on pushes and pull requests.

For a Docker-backed end-to-end test, run:

```bash
./scripts/smoke-test.sh
```

## Grading rules

Prefer observable system-state checks over source-code matching. Examples include users/groups, ownership and permissions, generated files, service configuration, and repeat behavior.

Only inspect Bash source/AST when a specific language construct is itself a learning objective.

For idempotency marks, a second zero exit code is not enough. The required state must be correct after the first run and remain correct after the second run.

## Versioning

Once a lab version has been used for a graded course run, do not silently change its grading semantics. Increment its version (or create a new lab version) so historical submissions remain reproducible.

The runner records a SHA-256 of grading-relevant lab content and the submitted script for replay/audit purposes.

## Student secrecy boundary

Never expose these to the student workspace:

- `grader.py`;
- hidden fixtures;
- reference solutions;
- expected data that reveals hidden cases.

The standalone runner copies only temporary trusted setup code and the student's own submission into the execution container. Hidden grading runs outside the student container.

## Setup variables

Generated variables declared in `lab.yaml` are supplied to trusted `setup.sh` as environment variables. Student code does **not** automatically inherit these variables; pass only the values the student is supposed to receive through `execution.command` arguments.

All random generators are seed-reproducible. Use `--seed` while debugging a grader so the exact hidden case can be replayed.

## Module consistency

`course.yaml` is the authoritative module catalog. A lab's `module:` field must match the module directory under which it is discovered, and lab IDs must be unique across the repository.
