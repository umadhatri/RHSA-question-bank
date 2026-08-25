# Question Bank v0.3

The first question-bank release contains five contract-v1 Bash labs. Each lab runs in a disposable Rocky Linux 9 grading container and is graded from observable postconditions rather than expected command strings.

| Lab | Module | Difficulty | Primary skills |
|---|---|---|---|
| `RHSA-SHELL-001` | Shell Basics | Beginner | arguments, tests, globbing, hidden files, `mkdir`, `mv`, idempotency |
| `RHSA-FILE-001` | Files & Permissions | Beginner | `chgrp`, `chmod`, setgid directories, preserving existing data |
| `RHSA-USERS-001` | Users & Groups | Beginner | users, groups, login shell, supplementary groups, shared directories |
| `RHSA-TEXT-001` | Text Processing | Beginner | log filtering, extraction, counting, sorting, deterministic reports |
| `RHSA-BACKUP-001` | Archives & Backups | Beginner | `tar`, gzip, recursive trees, dotfiles, safe repeat execution |

## Authoring direction

The bank should grow in course order and keep one principle consistent: **grade the resulting Linux state or artifact, not a particular command spelling**. Source-code/AST inspection should only be added when use of a specific Bash construct is itself an explicit learning objective.

Candidate next modules include processes/signals, scheduled tasks, service configuration, package inspection, SSH configuration, and network diagnostics. Labs that require faithful SELinux, LVM, bootloader, kernel, or full NetworkManager behavior should eventually use a VM-backed grader rather than forcing those concepts into containers.
