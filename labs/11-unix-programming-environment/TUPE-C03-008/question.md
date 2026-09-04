# TUPE-C03-008 — Output Stream Router

Write a Bash script named `route_streams.sh` with this command-line interface:

```text
route_streams.sh STDOUT_FILE STDERR_FILE EMITTER_COMMAND
```

The grading environment provides an executable `EMITTER_COMMAND` that writes
different records to standard output and standard error.

Your script must run `EMITTER_COMMAND` and route its two output streams
independently:

- standard output must go only to `STDOUT_FILE`
- standard error must go only to `STDERR_FILE`

Requirements:

- Treat all three parameters as runtime values; do not hard-code grading paths.
- Preserve the exact text emitted on each stream.
- Do not merge standard error into standard output.
- Do not swap the two streams.
- Replace any previous contents of both output files; do not append to stale
  output.
- Do not modify the provided emitter command.
- Running the script again with the same arguments must preserve the same
  correct files.
- Your script will be invoked more than once with different emitter commands
  during the same grading run.

This lab focuses on the additional I/O redirection material in Chapter 3.7 of
*The Unix Programming Environment*, especially the distinction between file
descriptor 1 (standard output) and file descriptor 2 (standard error).

Your submission is graded by observable behavior. Equivalent shell
implementations are accepted.

You may create and edit the script entirely from the terminal using an editor
such as `vi`, `vim`, or `nano`.
