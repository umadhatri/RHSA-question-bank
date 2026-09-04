# TUPE-C03-009 — Here-Document Generator

Write a Bash script named `make_notice.sh` with this command-line interface:

```text
make_notice.sh OUTPUT_FILE PROJECT OWNER
```

Your script must create `OUTPUT_FILE` with exactly this seven-line structure:

```text
BEGIN NOTICE
project=PROJECT
owner=OWNER
home-literal=$HOME
command-literal=$(date)
backtick-literal=`whoami`
END NOTICE
```

`PROJECT` and `OWNER` in the structure above are placeholders. Replace them
with the values supplied as the second and third command-line arguments.

The three shell-looking values on the following lines are **literal text** and
must appear exactly as shown:

```text
home-literal=$HOME
command-literal=$(date)
backtick-literal=`whoami`
```

In particular:

- do not expand `$HOME`
- do not execute `date`
- do not execute `whoami`
- preserve spaces and metacharacters inside the supplied `PROJECT` and `OWNER`
  arguments
- replace any previous contents of `OUTPUT_FILE`; do not append
- running the script again with the same arguments must produce the same exact
  file
- your script will be invoked more than once with different arguments during
  the same grading run

This lab focuses on here documents and shell expansion rules from Chapter 3.7
of *The Unix Programming Environment*. A here document is a natural way to
write a fixed multi-line block while selectively allowing or preventing shell
expansion.

Your submission is graded by observable behavior. Equivalent shell
implementations are accepted; the grader does not require one particular
here-document delimiter or implementation style.

You may create and edit the script entirely from the terminal using an editor
such as `vi`, `vim`, or `nano`.
