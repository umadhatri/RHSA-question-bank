# Changelog

## 0.3.0 — First question-bank release

- Expanded from one reference lab to five course-bank labs.
- Added shell/file organization, permissions, log-analysis, and backup graders.
- Added seed-reproducible `random_token`, `random_ipv4`, and `random_int` variables.
- Passed generated variables to trusted `setup.sh` as environment variables.
- Added snapshot helpers for regular-file checks and path enumeration.
- Added module/id consistency validation across `course.yaml`.
- Expanded grader unit tests and end-to-end smoke testing across all reference solutions.
- Expanded the Rocky Linux base image with `gawk`, `sed`, `tar`, and `gzip`.

## 0.2.0 — Contract v1

- Formalized lab/result schemas and strong idempotency semantics.
- Added repository validation, CI, templates, reproducibility metadata, and unit tests.

## 0.1.0 — Proof of concept

- Implemented `RHSA-USERS-001` with disposable Docker execution and host-side state grading.
