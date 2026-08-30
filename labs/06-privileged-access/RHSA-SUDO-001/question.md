# RHSA-SUDO-001 — Scoped Privileged Access

Write a Bash script named `configure_sudo.sh`.

Your script will be executed as:

    bash configure_sudo.sh USERNAME

`USERNAME` is chosen by the grading system at submission time. Do not hard-code a username.

The specified user already exists.

A root-owned maintenance command is already installed at:

    /usr/local/sbin/cyberrange-maintenance

## Requirements

Configure delegated administrative access for `USERNAME`.

Your script must:

1. Create `/etc/sudoers.d/cyberrange-USERNAME`, where `USERNAME` is the supplied argument.
2. Grant `USERNAME` passwordless sudo access to only `/usr/local/sbin/cyberrange-maintenance`.
3. Allow that command to run as `root`.
4. Set the sudoers drop-in ownership to `root:root`.
5. Set its mode to `0440`.
6. Leave `/etc/sudoers` unchanged.
7. Do not add the user to the `wheel` group.
8. Do not grant unrestricted sudo access such as `NOPASSWD: ALL`.
9. Leave the complete sudo configuration syntactically valid.
10. Exit successfully when run again with the same username.

Your solution must be a Bash script. All work should be performed from the terminal.

## Submission

    submit configure_sudo.sh

For the standalone development runner:

    python3 grader/runner.py \
      --lab labs/06-privileged-access/RHSA-SUDO-001 \
      --submission configure_sudo.sh
