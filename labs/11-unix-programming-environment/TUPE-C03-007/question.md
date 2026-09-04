# TUPE-C03-007 — Environment and PATH Repair

Write a Bash script named `environment_runner.sh` with this command-line
interface:

```text
environment_runner.sh OUTPUT_FILE TOOL_DIRECTORY CHILD_COMMAND SESSION_VALUE
```

The grading environment starts your script with an existing `PATH`. That path
contains:

- a decoy command named `range-tool`,
- a separate legacy directory containing `legacy-helper`, and
- the normal system command directories.

`TOOL_DIRECTORY` contains the correct `range-tool` for the current invocation.
`CHILD_COMMAND` is an executable probe program that inspects the environment it
inherits.

Your script must prepare the environment and then execute `CHILD_COMMAND`.

Requirements:

- Prepend `TOOL_DIRECTORY` to the current `PATH`.
- Preserve every existing `PATH` entry and preserve their original order after
  the new leading entry.
- Make the updated `PATH` available to `CHILD_COMMAND`.
- Set the shell variable `TUPE_SESSION` to `SESSION_VALUE`.
- Make `TUPE_SESSION` available to `CHILD_COMMAND`.
- Execute `CHILD_COMMAND` and replace the contents of `OUTPUT_FILE` with its
  standard output.
- Do not modify the supplied tool, decoy, legacy helper, or child probe.
- Running the script again with the same arguments must produce the same
  correct output.
- Your script will be invoked twice with different tool directories and session
  values during one grading run.

Why the ordering matters: appending `TOOL_DIRECTORY` would leave the decoy
`range-tool` earlier in the search path. Replacing `PATH` instead of extending
it would make the legacy helper unavailable.

This lab focuses on shell variables, `PATH`, and exported environment variables
as introduced in Chapter 3.6 of *The Unix Programming Environment*.

Your submission is graded by observable behavior. Equivalent shell
implementations that produce the required child environment are accepted.

You may create and edit the script entirely from the terminal using an editor
such as `vi`, `vim`, or `nano`.
