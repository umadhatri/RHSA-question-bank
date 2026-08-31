# RHSA-SSH-001 — SSH Public Key Provisioning

Write a Bash script named `configure_ssh_key.sh`.

Your script will be executed as:

    bash configure_ssh_key.sh USERNAME PUBLIC_KEY_FILE

`USERNAME` is chosen by the grading system.

The specified user already exists and already has one authorized SSH key.

`PUBLIC_KEY_FILE` contains an additional public key that must be granted access.

## Requirements

Your script must:

1. Preserve the existing user account.
2. Ensure the user's `.ssh` directory exists.
3. Set `.ssh` ownership to the user and the user's primary group.
4. Set `.ssh` mode to `0700`.
5. Ensure `.ssh/authorized_keys` exists.
6. Set `authorized_keys` ownership to the user and the user's primary group.
7. Set `authorized_keys` mode to `0600`.
8. Preserve the existing authorized key.
9. Add the key from `PUBLIC_KEY_FILE` exactly once.
10. Do not add any other SSH keys.
11. Do not modify the supplied public-key file.
12. Do not modify global SSH daemon configuration.
13. Exit successfully when run again with the same arguments.

Do not replace the existing `authorized_keys` contents.

Your solution must be a Bash script. All work should be performed from the terminal.

## Submission

    submit configure_ssh_key.sh

For the standalone development runner:

    python3 grader/runner.py \
      --lab labs/09-ssh-access/RHSA-SSH-001 \
      --submission configure_ssh_key.sh
