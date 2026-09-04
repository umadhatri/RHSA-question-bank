# TUPE-C03-010 — Batch File Processor

Write a Bash script named `batch_report.sh` with this command-line interface:

```text
batch_report.sh OUTPUT_FILE INPUT_FILE...
```

The first argument is the report to create. Every remaining argument is an
input file that must be processed.

For each input file, in the exact order supplied on the command line, append
exactly these two lines to the report:

```text
FILE=BASENAME
LINES=COUNT
```

where:

- `BASENAME` is the input file's basename, not its full path
- `COUNT` is the number of newline-terminated lines in that file

For example, if `one.txt` has 2 lines and `two.txt` has 4 lines, the report is:

```text
FILE=one.txt
LINES=2
FILE=two.txt
LINES=4
```

Requirements:

- Process every supplied input file exactly once.
- Do not assume a fixed number of input files.
- Preserve the command-line argument order.
- Input filenames may contain spaces and shell metacharacters such as `*`,
  `[` and `]`, and `$`; treat those characters literally.
- Process only the files supplied as arguments. Do not scan or glob the whole
  directory for additional files.
- Do not modify the supplied input files.
- Replace any previous contents of `OUTPUT_FILE`; do not append to stale
  output from an earlier run.
- Running the script again with the same arguments must produce the same exact
  report.
- Your script will be invoked more than once with different-sized input lists
  during the same grading run.

This lab focuses on the shell `for` loop material in Chapter 3.8 of *The Unix
Programming Environment*. A natural solution iterates over the remaining
positional parameters after separating the output filename.

Your submission is graded by observable behavior. Equivalent shell
implementations are accepted.

You may create and edit the script entirely from the terminal using an editor
such as `vi`, `vim`, or `nano`.
