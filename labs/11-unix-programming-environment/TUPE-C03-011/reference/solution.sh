#!/usr/bin/env bash
set -euo pipefail

[[ $# -ge 2 ]] || {
    echo "Usage: bundle_builder.sh OUTPUT_BUNDLE INPUT_FILE..." >&2
    exit 2
}

output=$1
shift

printf '#!/usr/bin/env bash\nset -euo pipefail\n\n' > "$output"

index=0
for file in "$@"; do
    index=$((index + 1))
    name=$(basename -- "$file")
    delimiter="__TUPE_BUNDLE_${index}__"

    while grep -Fxq -- "$delimiter" "$file"; do
        delimiter="${delimiter}_X"
    done

    printf "cat > %q <<'%s'\n" "$name" "$delimiter" >> "$output"
    cat -- "$file" >> "$output"
    printf '%s\n\n' "$delimiter" >> "$output"
done
