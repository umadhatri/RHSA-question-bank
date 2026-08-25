# RHSA-BACKUP-001 — Automated Compressed Backup

Write a Bash script named `create_backup.sh` that accepts:

```text
create_backup.sh SOURCE_DIRECTORY DESTINATION_DIRECTORY ARCHIVE_NAME
```

Your script must:

- Verify that the source directory exists.
- Create the destination directory if necessary.
- Create a **gzip-compressed tar archive** at `DESTINATION_DIRECTORY/ARCHIVE_NAME`.
- Include the complete contents of the source directory recursively, including hidden files.
- Store paths relative to the source directory; do not archive the source directory's absolute host path.
- Do not add unrelated files to the archive.
- Running the script again with the same arguments must succeed and replace/update the requested archive without creating additional backup files.

The source path, destination path, archive name, and source contents vary during grading. Do not hard-code them.
