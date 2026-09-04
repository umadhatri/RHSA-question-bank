from __future__ import annotations

from typing import Any

from grader.api import GradeBook, RootfsSnapshot, SnapshotSet


def source_spec(token: str) -> list[tuple[str, bytes]]:
    base = f"/workspace/bundle_sources_{token}"
    return [
        (
            f"{base}/alpha note.txt",
            (
                f"alpha-{token}\n"
                "$HOME must remain literal\n"
                "$(date) must remain literal\n"
                "EOF\n"
            ).encode(),
        ),
        (
            f"{base}/beta[2].conf",
            (
                f"beta-{token}\n"
                "backtick: `whoami`\n"
                "single quote: 'alpha'\n"
                'double quote: "beta"\n'
                "backslash: \\\n"
            ).encode(),
        ),
        (
            f"{base}/gamma*.txt",
            (
                f"gamma-{token} first\n"
                "\n"
                "middle blank line above\n"
                "__TUPE_BUNDLE_3__\n"
                "gamma final\n"
            ).encode(),
        ),
        (
            f"{base}/delta dollar$.txt",
            (
                f"delta-{token}\n"
                "END_BUNDLE\n"
                "$literal * [brackets]\n"
            ).encode(),
        ),
        (
            f"{base}/epsilon-empty.txt",
            b"",
        ),
        (
            f"{base}/decoy-not-supplied.txt",
            (
                f"DECOY-{token}\n"
                "this file must never be bundled\n"
            ).encode(),
        ),
    ]


def extraction_state(
    snapshot: RootfsSnapshot,
    directory: str,
    expected_sources: list[tuple[str, bytes]],
) -> dict[str, Any]:
    expected_paths = {
        f"{directory}/{source_path.rsplit('/', 1)[-1]}"
        for source_path, _content in expected_sources
    }

    actual_paths = set(snapshot.paths_under(directory))

    contents = {
        source_path.rsplit("/", 1)[-1]: snapshot.read_bytes(
            f"{directory}/{source_path.rsplit('/', 1)[-1]}"
        )
        for source_path, _content in expected_sources
    }

    expected_contents = {
        source_path.rsplit("/", 1)[-1]: content
        for source_path, content in expected_sources
    }

    return {
        "paths_exact": actual_paths == expected_paths,
        "contents_exact": contents == expected_contents,
        "contents": contents,
    }


def state(
    snapshot: RootfsSnapshot,
    variables: dict[str, Any],
) -> dict[str, Any]:
    token = str(variables["TEST_TOKEN"])
    sources = source_spec(token)

    bundle_short_path = f"/workspace/bundle_short_{token}.sh"
    bundle_long_path = f"/workspace/bundle_long_{token}.sh"
    extract_short = f"/workspace/extract_short_{token}"
    extract_long = f"/workspace/extract_long_{token}"

    bundle_short = snapshot.read_bytes(bundle_short_path)
    bundle_long = snapshot.read_bytes(bundle_long_path)

    short = extraction_state(snapshot, extract_short, sources[:2])
    long = extraction_state(snapshot, extract_long, sources[:5])

    sources_preserved = all(
        snapshot.read_bytes(path) == expected
        and snapshot.mode(path) == 0o644
        for path, expected in sources
    )

    alpha = short["contents"].get("alpha note.txt")
    beta = short["contents"].get("beta[2].conf")
    gamma = long["contents"].get("gamma*.txt")
    delta = long["contents"].get("delta dollar$.txt")
    epsilon = long["contents"].get("epsilon-empty.txt")

    literal_preservation = (
        alpha is not None
        and beta is not None
        and gamma is not None
        and delta is not None
        and b"$HOME must remain literal\n" in alpha
        and b"$(date) must remain literal\n" in alpha
        and b"EOF\n" in alpha
        and b"backtick: `whoami`\n" in beta
        and b"backslash: \\\n" in beta
        and b"__TUPE_BUNDLE_3__\n" in gamma
        and b"END_BUNDLE\n" in delta
        and b"$literal * [brackets]\n" in delta
    )

    bundles_created = (
        bundle_short is not None
        and len(bundle_short) > 0
        and bundle_long is not None
        and len(bundle_long) > 0
    )

    return {
        "bundle_short": bundle_short,
        "bundle_long": bundle_long,
        "bundles_created": bundles_created,
        "short_reconstruction": short["paths_exact"] and short["contents_exact"],
        "long_reconstruction": long["paths_exact"] and long["contents_exact"],
        "literal_preservation": literal_preservation,
        "empty_file": epsilon == b"",
        "no_extra_files": short["paths_exact"] and long["paths_exact"],
        "sources_preserved": sources_preserved,
    }


def grade(
    lab: dict[str, Any],
    context: dict[str, Any],
    snapshots: SnapshotSet,
) -> dict[str, Any]:
    book = GradeBook(lab)

    variables = context["variables"]
    first = state(snapshots["after_first"], variables)
    second = state(snapshots["after_second"], variables)

    first_run = context.get("first_run", {})
    second_run = context.get("second_run", {})

    first_rc = int(first_run.get("returncode", 1))
    second_rc = int(second_run.get("returncode", 1))

    book.check(
        "syntax",
        context.get("syntax_ok", False),
        "Bash syntax is valid.",
        "Bash syntax validation failed.",
    )

    book.check(
        "first_run_exit",
        first_rc == 0 and not first_run.get("timed_out", False),
        "Both bundles were generated and executed successfully on the first run.",
        f"The first generation/extraction run returned exit code {first_rc}.",
    )

    book.check(
        "bundles_created",
        first["bundles_created"],
        "Both requested self-contained bundle files were created.",
        "One or both requested bundle files were missing or empty.",
    )

    book.check(
        "short_reconstruction",
        first["short_reconstruction"],
        "The two-file bundle reconstructed exactly the two requested files.",
        "The two-file bundle did not reconstruct the requested files exactly.",
    )

    book.check(
        "long_reconstruction",
        first["long_reconstruction"],
        "The five-file bundle reconstructed every requested file exactly.",
        "The five-file bundle missed, changed, duplicated, or added content/files.",
    )

    book.check(
        "literal_preservation",
        first["literal_preservation"],
        "Shell-looking text and delimiter-like lines were preserved literally.",
        "Shell metacharacters, quoting, backslashes, or delimiter-like content was altered.",
    )

    book.check(
        "empty_file",
        first["empty_file"],
        "The supplied empty file was reconstructed as exactly zero bytes.",
        "The supplied empty file was missing or gained unintended content.",
    )

    book.check(
        "no_extra_files",
        first["no_extra_files"],
        "Each extraction contains only the files supplied to that bundle invocation.",
        "An unsupplied, decoy, duplicate, or otherwise extra path was reconstructed.",
    )

    book.check(
        "sources_preserved",
        first["sources_preserved"],
        "All supplied source and decoy files were preserved unchanged.",
        "One or more source/decoy files were modified or had permissions changed.",
    )

    idempotent = (
        first["bundles_created"]
        and first["short_reconstruction"]
        and first["long_reconstruction"]
        and second["bundles_created"]
        and second["short_reconstruction"]
        and second["long_reconstruction"]
        and first["sources_preserved"]
        and second["sources_preserved"]
        and first_rc == 0
        and second_rc == 0
        and not first_run.get("timed_out", False)
        and not second_run.get("timed_out", False)
        and first["bundle_short"] == second["bundle_short"]
        and first["bundle_long"] == second["bundle_long"]
    )

    book.check(
        "idempotency",
        idempotent,
        "Repeated generation and extraction preserves identical bundles and files.",
        "The second run changed a bundle, failed, or failed to preserve reconstructed state.",
    )

    return book.finalize()
