# RHSA and TUPE question review

This branch contains 21 existing questions and their current intended solve paths: 10 RHSA labs and 11 TUPE labs. The solve paths are the original `reference/solution.sh` scripts. Content is copied unchanged from commit `dcc167e`; any question/solution mismatches remain for review.

## Editing

Edit each `question.md` and its paired `reference/solution.sh` together. Keep the lab IDs and file paths unchanged so revisions can be brought back into the autograder. Commit and push your changes to `codex/questions-solve-path-review`.

These scripts describe the current solve paths; they may require fixtures, helper commands, privileges, and packages supplied by the full lab environment. This review branch omits setup, graders, tests, and runtime code.

## Bringing revisions back

This is a content-only review branch. Do not merge the branch wholesale into the application branch: its preparation commit removes runtime files. Instead, cherry-pick only the professor's subsequent content-edit commits, or restore the two reviewed files for each lab from this branch. Run the full autograder checks in the application checkout after integrating the revisions.

## Questions and intended solve paths

| Lab | Question | Intended solve path |
| --- | --- | --- |
| RHSA-SHELL-001 | [Question](labs/01-shell-basics/RHSA-SHELL-001/question.md) | [Solution](labs/01-shell-basics/RHSA-SHELL-001/reference/solution.sh) |
| RHSA-FILE-001 | [Question](labs/02-files-permissions/RHSA-FILE-001/question.md) | [Solution](labs/02-files-permissions/RHSA-FILE-001/reference/solution.sh) |
| RHSA-USERS-001 | [Question](labs/03-users-groups/RHSA-USERS-001/question.md) | [Solution](labs/03-users-groups/RHSA-USERS-001/reference/solution.sh) |
| RHSA-TEXT-001 | [Question](labs/04-text-processing/RHSA-TEXT-001/question.md) | [Solution](labs/04-text-processing/RHSA-TEXT-001/reference/solution.sh) |
| RHSA-BACKUP-001 | [Question](labs/05-archives-backups/RHSA-BACKUP-001/question.md) | [Solution](labs/05-archives-backups/RHSA-BACKUP-001/reference/solution.sh) |
| RHSA-SUDO-001 | [Question](labs/06-privileged-access/RHSA-SUDO-001/question.md) | [Solution](labs/06-privileged-access/RHSA-SUDO-001/reference/solution.sh) |
| RHSA-PROC-001 | [Question](labs/07-process-management/RHSA-PROC-001/question.md) | [Solution](labs/07-process-management/RHSA-PROC-001/reference/solution.sh) |
| RHSA-PKG-001 | [Question](labs/08-package-management/RHSA-PKG-001/question.md) | [Solution](labs/08-package-management/RHSA-PKG-001/reference/solution.sh) |
| RHSA-SSH-001 | [Question](labs/09-ssh-access/RHSA-SSH-001/question.md) | [Solution](labs/09-ssh-access/RHSA-SSH-001/reference/solution.sh) |
| RHSA-SCHED-001 | [Question](labs/10-scheduled-jobs/RHSA-SCHED-001/question.md) | [Solution](labs/10-scheduled-jobs/RHSA-SCHED-001/reference/solution.sh) |
| TUPE-C03-001 | [Question](labs/11-unix-programming-environment/TUPE-C03-001/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-001/reference/solution.sh) |
| TUPE-C03-002 | [Question](labs/11-unix-programming-environment/TUPE-C03-002/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-002/reference/solution.sh) |
| TUPE-C03-003 | [Question](labs/11-unix-programming-environment/TUPE-C03-003/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-003/reference/solution.sh) |
| TUPE-C03-004 | [Question](labs/11-unix-programming-environment/TUPE-C03-004/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-004/reference/solution.sh) |
| TUPE-C03-005 | [Question](labs/11-unix-programming-environment/TUPE-C03-005/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-005/reference/solution.sh) |
| TUPE-C03-006 | [Question](labs/11-unix-programming-environment/TUPE-C03-006/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-006/reference/solution.sh) |
| TUPE-C03-007 | [Question](labs/11-unix-programming-environment/TUPE-C03-007/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-007/reference/solution.sh) |
| TUPE-C03-008 | [Question](labs/11-unix-programming-environment/TUPE-C03-008/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-008/reference/solution.sh) |
| TUPE-C03-009 | [Question](labs/11-unix-programming-environment/TUPE-C03-009/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-009/reference/solution.sh) |
| TUPE-C03-010 | [Question](labs/11-unix-programming-environment/TUPE-C03-010/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-010/reference/solution.sh) |
| TUPE-C03-011 | [Question](labs/11-unix-programming-environment/TUPE-C03-011/question.md) | [Solution](labs/11-unix-programming-environment/TUPE-C03-011/reference/solution.sh) |
