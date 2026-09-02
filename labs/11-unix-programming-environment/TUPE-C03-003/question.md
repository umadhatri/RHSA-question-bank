# TUPE-C03-003 — Quoting and Literal Data

Write a Bash script named `quote_report.sh` that accepts exactly three positional arguments:

```text
quote_report.sh SOURCE_DIRECTORY OUTPUT_FILE LABEL
```

The grading environment deliberately passes arguments containing spaces and shell metacharacters.

`SOURCE_DIRECTORY` contains these four required files:

```text
customer name.txt
price$4.txt
pattern*.txt
question?.txt
```

The `*`, `?`, `$`, and spaces shown above are literal characters in the filenames.

The directory also contains similarly named decoy files. Your script must read the four exact filenames above rather than accidentally matching the decoys.

Create `OUTPUT_FILE` with exactly this structure:

```text
[LABEL]
LABEL_VALUE

[FILES]
customer=CONTENTS_OF_customer name.txt
price=CONTENTS_OF_price$4.txt
pattern=CONTENTS_OF_pattern*.txt
question=CONTENTS_OF_question?.txt
```

Requirements:

- Preserve the third positional argument exactly as it was received, including repeated spaces and metacharacters.
- Read the exact four required files.
- Preserve each file's one-line content exactly.
- Treat the special characters in the required filenames literally.
- Replace any previous contents of `OUTPUT_FILE`; do not append to stale output.
- Do not modify, rename, or delete files in `SOURCE_DIRECTORY`.
- Do not hard-code the randomized file contents or label.
- Running the script again with the same arguments must produce the same correct report.

This lab focuses on shell quoting. In particular, remember that unquoted expansions can undergo word splitting and filename generation, while quoting can protect spaces and metacharacters.

Your submission is graded by its observable behavior. Equivalent shell implementations are accepted.

You may create and edit the script entirely from the terminal using an editor such as `vi`, `vim`, or `nano`.
