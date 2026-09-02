# TUPE-C03-002 — Filename Pattern Selector

Write a Bash script named `select_patterns.sh` that accepts exactly two positional arguments:

```text
select_patterns.sh SOURCE_DIRECTORY OUTPUT_FILE
```

`SOURCE_DIRECTORY` contains a mixture of files whose names have deliberately similar forms.

Create `OUTPUT_FILE` with exactly these three sections, in this order:

```text
[SINGLE_CHAR_LOGS]
...

[NUMBERED_REPORTS]
...

[BACKUPS]
...
```

The sections must contain filenames only, not full paths.

## SINGLE_CHAR_LOGS

Include every non-hidden filename that matches this shell-style rule:

```text
app?.log
```

The `?` represents exactly one character.

Sort the selected filenames in ascending lexicographic order.

## NUMBERED_REPORTS

Include every non-hidden filename that matches:

```text
report[0-9].txt
```

Only a single decimal digit is allowed between `report` and `.txt`.

Sort the selected filenames in ascending lexicographic order.

## BACKUPS

Include every non-hidden filename ending exactly in:

```text
.old
```

Files whose names continue after `.old` must not be included.

Leading-dot files must not be included.

Sort the selected filenames in ascending lexicographic order.

## Additional requirements

- Replace any previous contents of `OUTPUT_FILE`; do not append to stale output.
- Do not modify, rename, or delete files in `SOURCE_DIRECTORY`.
- The filenames used by the grading environment vary between attempts.
- Do not hard-code the expected filenames.
- Running the script again with the same arguments must produce the same correct report.

This lab is designed to practice Unix shell filename generation and metacharacters. Your submission is graded by its observable result, so equivalent shell implementations are accepted.

You may create and edit the script entirely from the terminal using an editor such as `vi`, `vim`, or `nano`.
