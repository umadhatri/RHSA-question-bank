# TUPE-C03-005 — Argument Manifest Builder

Write a Bash script named `argument_manifest.sh` with this command-line interface:

```text
argument_manifest.sh OUTPUT_FILE LABEL ITEM [ITEM ...]
```

The first two positional arguments have fixed meanings:

1. `OUTPUT_FILE` — where the manifest must be written.
2. `LABEL` — the label to place in the manifest.

Every argument after `LABEL` is an item.

Your script must require at least one item and create `OUTPUT_FILE` in this exact format:

```text
LABEL=LABEL_VALUE
COUNT=NUMBER_OF_ITEMS
1=FIRST_ITEM
2=SECOND_ITEM
3=THIRD_ITEM
...
```

For example, if the command receives three item arguments, the manifest must contain three numbered item lines.

Requirements:

- `COUNT` must equal the number of item arguments actually supplied.
- Process every item argument; do not assume a fixed number of items.
- Preserve the original item order.
- Number items starting at `1`.
- Replace any previous contents of `OUTPUT_FILE`; do not append to stale output.
- Do not hard-code the labels, item values, item count, or grading paths.
- Running the script again with the same arguments must produce the same correct manifest.

The grading environment will invoke your script with different numbers of item arguments during the same grading run.

This lab focuses on shell command arguments and positional parameters. A typical solution will need to distinguish the fixed positional parameters from the remaining argument list.

Your submission is graded by observable behavior. Equivalent shell implementations are accepted.

You may create and edit the script entirely from the terminal using an editor such as `vi`, `vim`, or `nano`.
