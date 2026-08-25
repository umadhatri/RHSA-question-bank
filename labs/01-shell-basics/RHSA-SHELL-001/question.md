# RHSA-SHELL-001 — File Organizer

Write a Bash script named `organize_files.sh` that accepts exactly two positional arguments:

```text
organize_files.sh SOURCE_DIRECTORY DESTINATION_DIRECTORY
```

Your script must organize the **regular files directly inside** the source directory as follows:

- Create `text`, `logs`, and `other` subdirectories inside the destination directory when necessary.
- Move files whose names end in `.txt` into `DESTINATION_DIRECTORY/text/`.
- Move files whose names end in `.log` into `DESTINATION_DIRECTORY/logs/`.
- Move every other regular file, **including hidden files**, into `DESTINATION_DIRECTORY/other/`.
- Do not fail when one of the categories contains no files.
- Do not move directories from the source directory.
- After a successful run, no regular files that were present at the top level of the source directory should remain there.
- Running the script again with the same arguments must succeed and preserve the correct organization.

The grading system uses different source and destination paths on each attempt. Do not hard-code filenames or paths.

You may create and edit the script entirely from the terminal using an editor such as `vi`, `vim`, or `nano`.
