# Grader Contract v1

This document is the compatibility boundary between course questions and the CyberRange grading engine.

## Lab package

Every graded question contains:

```text
RHSA-XXXX-001/
├── question.md
├── lab.yaml
├── setup.sh
├── grader.py
├── fixtures/
└── reference/          # instructor-only, excluded from grading hash
```

`lab.yaml` must declare `contract_version: 1` and validate against `schemas/lab.schema.json`.

## Grader entry point

Every hidden checker exports exactly:

```python
def grade(lab, context, snapshots):
    ...
```

- `lab`: parsed `lab.yaml`.
- `context`: execution metadata, randomized variables, syntax result, and run results.
- `snapshots`: a `SnapshotSet` containing `after_first` and `after_second` read-only root-filesystem snapshots.

The grader returns the result of `GradeBook.finalize()`.

## Lifecycle

1. Create a pristine grading container.
2. Run trusted `setup.sh` and remove it.
3. Copy only the student submission into `/submission`.
4. Run `bash -n`.
5. Execute the submission once with hidden/randomized inputs.
6. Export `after_first`.
7. Execute the same submission again with the same inputs.
8. Export `after_second`.
9. Stop the container.
10. Run hidden `grader.py` on the host against both snapshots.
11. Emit result contract v1 JSON.
12. Destroy the container and temporary snapshots.

## Idempotency definition

For contract v1, idempotency means more than a zero exit code on the second run. A lab that awards idempotency marks must verify that:

- the first execution succeeds;
- the first execution establishes the complete required state;
- the second execution succeeds; and
- the complete required state remains correct after the second execution.

## Grading principles

Prefer observable postconditions over source matching. Regex checks should not be used as the primary correctness mechanism. Syntax-tree/source checks are appropriate only where a specific Bash construct is itself a learning objective.

## Reproducibility metadata

Every result records at least:

- random seed and generated variables;
- student submission SHA-256;
- grading-relevant lab-package SHA-256;
- container image name and local image ID;
- first and second execution metadata.

This information is intended to make disputed grades replayable later.
