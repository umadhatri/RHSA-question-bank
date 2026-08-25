# RHSA-FILE-001 — Secure Shared Project Directory

Write a Bash script named `secure_project.sh` that accepts:

```text
secure_project.sh PROJECT_DIRECTORY GROUP_NAME
```

The group supplied to the script already exists. The project directory may already contain data and your script must **not destroy or replace existing file contents**.

Configure the project as follows:

- Ensure `PROJECT_DIRECTORY` exists.
- Set the project's group ownership to `GROUP_NAME`.
- Set the project directory mode to `2770` (setgid, full access for owner/group, no access for others).
- Ensure `PROJECT_DIRECTORY/README.txt` exists. If it already exists, preserve its contents.
- Set `README.txt` group ownership to `GROUP_NAME` and mode to `0660`.
- Ensure `PROJECT_DIRECTORY/archive` exists.
- Set the `archive` directory group ownership to `GROUP_NAME` and mode to `2750`.
- Running the script repeatedly with the same arguments must succeed and preserve the required state and existing README contents.

The grading system varies the project path and group name between attempts. Do not hard-code them.
