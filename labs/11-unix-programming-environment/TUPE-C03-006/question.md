# TUPE-C03-006 — Dynamic Command Report

Write a Bash script named `dynamic_report.sh` with this command-line interface:

```text
dynamic_report.sh OUTPUT_FILE PRODUCER_COMMAND FORMATTER_COMMAND
```

The grading environment provides two executable helper commands:

- `PRODUCER_COMMAND` prints one dynamically generated line to standard output.
- `FORMATTER_COMMAND` accepts exactly one argument and prints a formatted record.

Your script must run `PRODUCER_COMMAND`, use the text it prints as the single
argument to `FORMATTER_COMMAND`, and write the formatter's standard output to
`OUTPUT_FILE`.

Requirements:

- Treat `PRODUCER_COMMAND` and `FORMATTER_COMMAND` as command paths supplied at
  runtime; do not hard-code their names or grading paths.
- Preserve the producer's output exactly when passing it to the formatter.
- The producer output may contain spaces and shell metacharacters such as `*`,
  `$`, `[` and `]`; it must still arrive at the formatter as one argument.
- Replace any previous contents of `OUTPUT_FILE`; do not append to stale output.
- Do not modify either provided helper command.
- Running the script again with the same arguments must produce the same correct
  output.
- Your script will be invoked more than once with different producer commands
  during the same grading run.

This lab focuses on using program output as command arguments, as introduced in
Chapter 3.5 of *The Unix Programming Environment*.

Your submission is graded by observable behavior. Equivalent shell
implementations are accepted.

You may create and edit the script entirely from the terminal using an editor
such as `vi`, `vim`, or `nano`.
