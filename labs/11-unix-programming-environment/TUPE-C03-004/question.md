# TUPE-C03-004 — Personal Command Installer

Write a Bash script named `install_recordcount.sh` that accepts exactly one positional argument:

```text
install_recordcount.sh BIN_DIRECTORY
```

Your installer must create a reusable command named:

```text
recordcount
```

inside `BIN_DIRECTORY`.

The installed `recordcount` command must:

- Be an executable shell program.
- Accept exactly one positional argument: a path to a regular file.
- Print the number of lines in that file as a decimal integer.
- Exit successfully when given a valid file.
- Work when invoked by the command name `recordcount`, not only through an explicit pathname.

The grading environment will:

1. Run your installer.
2. Add the supplied `BIN_DIRECTORY` to the front of `PATH`.
3. Change to a different working directory.
4. Resolve `recordcount` by name.
5. Invoke it on multiple files containing different randomized numbers of lines.

Additional requirements:

- Create `BIN_DIRECTORY` if it does not already exist.
- Do not modify the input data files.
- Do not hard-code the expected line counts or grading paths.
- Running the installer again with the same `BIN_DIRECTORY` must still succeed and leave a working `recordcount` command.

This lab focuses on creating new Unix commands and making them available through `PATH`.

Your submission is graded by observable behavior. Equivalent shell implementations are accepted.

You may create and edit the installer entirely from the terminal using an editor such as `vi`, `vim`, or `nano`.
