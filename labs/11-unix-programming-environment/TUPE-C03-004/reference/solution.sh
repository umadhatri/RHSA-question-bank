#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || {
    echo "Usage: install_recordcount.sh BIN_DIRECTORY" >&2
    exit 2
}

bin_dir=$1

mkdir -p -- "$bin_dir"

cat > "$bin_dir/recordcount" <<'COMMAND'
#!/usr/bin/env bash
set -euo pipefail

[[ $# -eq 1 ]] || {
    echo "Usage: recordcount FILE" >&2
    exit 2
}

file=$1

[[ -f "$file" ]] || {
    echo "Not a regular file: $file" >&2
    exit 2
}

awk 'END { print NR }' "$file"
COMMAND

chmod 0755 "$bin_dir/recordcount"
