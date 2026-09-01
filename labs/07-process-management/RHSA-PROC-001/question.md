# RHSA-PROC-001 — Process Management and Priority

Write a Bash script named `manage_processes.sh`.

The grading environment contains three long-running processes:

- `cr_runaway`
- `cr_worker`
- `cr_control`

## Requirements

Your script must:

1. Terminate the running `cr_runaway` process.
2. Keep the existing `cr_worker` process running.
3. Set the existing `cr_worker` process nice value to `10`.
4. Keep the existing `cr_control` process running.
5. Leave the `cr_control` nice value unchanged at `0`.
6. Do not replace or restart the worker or control process.
7. Do not create additional processes named `cr_runaway`, `cr_worker`, or `cr_control`.
8. Exit successfully if executed again after the required state has already been established.

Use normal Linux process-management tools such as `ps`, `pgrep`, `kill`, and `renice`.

Your solution must be a Bash script. All work should be performed from the terminal.

## Submission

```bash
submit manage_processes.sh
```

For the standalone development runner:
```bash
python3 grader/runner.py --lab labs/07-process-management/RHSA-PROC-001 --submission manage_processes.sh
```