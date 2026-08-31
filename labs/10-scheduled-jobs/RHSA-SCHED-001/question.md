# RHSA-SCHED-001 — Scheduled Maintenance

Write a Bash script named `configure_schedule.sh`.

Your script will be executed as:

    bash configure_schedule.sh USERNAME HOUR MINUTE

`USERNAME`, `HOUR`, and `MINUTE` are chosen by the grading system.

The specified user already exists.

A maintenance command is installed at:

    /usr/local/sbin/cyberrange-maintenance

The cron configuration already contains an unrelated weekly audit job that must be preserved.

## Requirements

Your script must:

1. Configure the cron file:

       /etc/cron.d/cyberrange-maintenance

2. Preserve the existing weekly audit job exactly.
3. Add a daily job that runs at the supplied `HOUR` and `MINUTE`.
4. Run the daily job as `USERNAME`.
5. Execute exactly:

       /usr/local/sbin/cyberrange-maintenance

6. Add the required daily job exactly once.
7. Do not add any other jobs to the managed cron file.
8. Set the cron file ownership to `root:root`.
9. Set the cron file mode to `0644`.
10. Do not modify either maintenance command.
11. Do not move the job into a per-user crontab or modify unrelated cron configuration.
12. Preserve the existing user account.
13. Exit successfully when run again with the same arguments.

Your solution must be a Bash script. All work should be performed from the terminal.

## Submission

    submit configure_schedule.sh

For the standalone development runner:

    python3 grader/runner.py \
      --lab labs/10-scheduled-jobs/RHSA-SCHED-001 \
      --submission configure_schedule.sh
