# RHSA-USERS-001 — User and Group Provisioning

Write a Bash script named `provision_user.sh`.

Your script will be executed as:

```bash
bash provision_user.sh USERNAME GROUPNAME
```

The values of `USERNAME` and `GROUPNAME` are chosen by the grading system at submission time. Do not hard-code specific names.

## Requirements

Your script must:

1. Create `GROUPNAME` if the group does not already exist.
2. Create `USERNAME` if the user does not already exist.
3. Configure `/bin/bash` as the user's login shell.
4. Make the user a member of `GROUPNAME`.
5. Create the directory `/srv/GROUPNAME`.
6. Set the group ownership of `/srv/GROUPNAME` to `GROUPNAME`.
7. Set the directory mode to `2770`.
8. Exit successfully when run again with the same arguments.

Your solution must be a Bash script. All work should be performed from the terminal.

## Submission

```bash
submit provision_user.sh
```

For the standalone development runner, the equivalent command is:

```bash
python3 grader/runner.py \
  --lab labs/01-users-groups/RHSA-USERS-001 \
  --submission provision_user.sh
```
