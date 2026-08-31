# RHSA-PKG-001 — Local RPM Package Deployment

Write a Bash script named `manage_package.sh`.

Your script will be executed as:

    bash manage_package.sh RPM_FILE

`RPM_FILE` is the path to a locally supplied RPM package.

The grading environment has no network access. Do not depend on external package repositories.

## Requirements

Your script must:

1. Install the RPM package supplied as `RPM_FILE`.
2. Ensure the package `cyberrange-monitor` is registered in the RPM database.
3. Ensure the installed version, release, and architecture match the supplied RPM.
4. Leave the package-managed executable unchanged:

       /usr/local/bin/cyberrange-monitor

5. Leave the package-managed configuration file unchanged:

       /etc/cyberrange-monitor.conf

6. Do not modify or replace the supplied RPM file.
7. Do not fake package installation by only copying package files.
8. Exit successfully when run again after the correct package is already installed.

Your solution must be a Bash script. All work should be performed from the terminal.

## Submission

    submit manage_package.sh

For the standalone development runner:

    python3 grader/runner.py \
      --lab labs/08-package-management/RHSA-PKG-001 \
      --submission manage_package.sh
