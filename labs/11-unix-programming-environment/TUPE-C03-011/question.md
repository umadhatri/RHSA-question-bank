# TUPE-C03-011 — Self-Contained Bundle Builder

Write a Bash script named `bundle_builder.sh` with this command-line interface:

```text
bundle_builder.sh OUTPUT_BUNDLE INPUT_FILE...
```

Your script must create `OUTPUT_BUNDLE`, which itself is a shell script.
Running the generated bundle in an empty directory must reconstruct every
supplied input file there using the input file's **basename** and **exact
contents**.

For example:

```text
bundle_builder.sh archive.sh one.txt "two notes.txt"
mkdir restored
cd restored
bash ../archive.sh
```

must recreate:

```text
one.txt
two notes.txt
```

with byte-for-byte equivalent contents.

Requirements:

- `OUTPUT_BUNDLE` must be a self-contained shell program. The original input
  files may be unavailable when the generated bundle is executed.
- Process every supplied input file exactly once.
- Do not assume a fixed number of input files.
- Use each input file's basename as the reconstructed filename.
- Preserve filenames containing spaces and shell metacharacters such as `*`,
  `[` and `]`, and `$`.
- Preserve file contents literally. Test data may contain text such as `$HOME`,
  `$(date)`, backticks, quotes, backslashes, blank lines, and lines that look
  like common here-document delimiters such as `EOF`.
- Correctly reproduce an empty input file as an empty output file.
- Do not include files that were not supplied as command-line arguments.
- Do not modify the supplied source files.
- Replace any previous contents of `OUTPUT_BUNDLE`; do not append stale bundle
  text.
- Running your builder again with the same arguments must produce the same
  bundle, and executing that bundle again must preserve the same reconstructed
  files.
- Your builder will be invoked more than once with different-sized input lists
  during the same grading run.

This is the Chapter 3 capstone lab. It combines positional parameters, quoting,
loops, redirection, generated shell commands, and the `bundle` idea from
Chapter 3.9 of *The Unix Programming Environment*.

A here-document-based solution is natural, but the grader accepts any
self-contained shell implementation with the required observable behavior.
If you use here documents, remember that both shell expansion and delimiter
collisions must be handled correctly.

You may create and edit the script entirely from the terminal using an editor
such as `vi`, `vim`, or `nano`.
