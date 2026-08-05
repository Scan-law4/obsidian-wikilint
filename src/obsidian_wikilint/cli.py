"""Check an Obsidian-compatible vault for broken [[wikilinks]].

Exact-resolution linter. Deliberately does NOT use Vault.find_broken_links()
or get_note(): both run a fuzzy similar-name fallback regardless of the
strategy argument, which silently absorbs typos ([[peper]] -> pepper).
Verified against obsidianmd-parser 0.4.1 on 2026-08-04.

Resolution (strict, no fuzzy):
  - path-style targets ("agents/pepper"): file existence relative to the
    vault root, appending ".md" unless already present.
  - bare names ("pepper"): case-insensitive lookup in a name index built
    from the public Vault.file_paths property (stems for .md, full names
    for attachments). >1 match = ambiguous, reported as broken.
  - empty target ([[#heading]]): same-page link, trivially valid.

Known Phase 1 limitation: frontmatter aliases are NOT resolved (the parser
does not index them); alias links are reported as broken.

Exit codes:
    0  vault clean
    1  broken links found
    2  environment error (vault path missing, 0 notes indexed, ...)
"""
from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

from obsidian_wikilint.vault_compat import VaultCompat

__version__ = "0.1.0"


def is_excluded(path: Path, excludes: set[str]) -> bool:
    """Component-based exclude. Applies to which notes are SCANNED;
    excluded notes remain valid link TARGETS (they stay in the index)."""
    return bool(excludes.intersection(path.parts))


def vault_relative(path, root: Path) -> Path:
    """Stable vault-relative paths for output and exclude matching."""
    p = Path(path)
    try:
        return p.relative_to(root)
    except ValueError:
        return p


def build_name_index(vault) -> dict[str, list[Path]]:
    """Case-insensitive name -> paths index from the PUBLIC file_paths
    property. .md files index by stem; every file indexes by full name,
    so embeds like [[image.png]] resolve too."""
    index: dict[str, list[Path]] = {}
    for p in vault.file_paths:
        index.setdefault(p.name.lower(), []).append(p)
        if p.suffix.lower() == ".md":
            index.setdefault(p.stem.lower(), []).append(p)
    return index


def resolve_strict(vault, index: dict[str, list[Path]],
                   target: str) -> tuple[bool, str]:
    """Strict resolution only. Returns (ok, reason). No fuzzy fallback."""
    if "/" in target:
        rel = target if target.lower().endswith(".md") else target + ".md"
        if (vault.path / rel).is_file():
            return True, ""
        # Path-style non-md attachment: [[dir/image.png]]
        if (vault.path / target).is_file():
            return True, ""
        return False, "not found"
    matches = index.get(target.lower(), [])
    if len(matches) == 1 or len({str(m) for m in matches}) == 1:
        return True, ""
    if len(matches) > 1:
        return False, "ambiguous (multiple notes match)"
    return False, "not found"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="wikilint",
        description="Check an Obsidian-compatible vault for broken [[wikilinks]].",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    parser.add_argument("vault", type=Path, help="Path to the vault root")
    parser.add_argument(
        "--exclude", action="append", default=[], metavar="DIR",
        help="Directory name to skip scanning (repeatable), e.g. _archive",
    )
    parser.add_argument("--json", action="store_true", help="JSON output on stdout")
    parser.add_argument(
        "--ignore-target", action="append", default=[], metavar="TARGET",
        help="Exact target string to never report (repeatable). For "
             "intentional non-note references: prose [[wikilinks]], "
             "shell fragments, cross-vault refs (SOUL.md).",
    )
    args = parser.parse_args()

    if not args.vault.is_dir():
        print(f"wikilint: error: vault path does not exist: {args.vault}",
              file=sys.stderr)
        sys.exit(2)

    vault = VaultCompat(args.vault)

    # obsidianmd-parser prints YAML/frontmatter warnings to STDOUT with
    # bare print(); on a vault with malformed frontmatter that corrupts
    # --json output. Route all parsing-phase stdout to stderr so stdout
    # carries only our result.
    with contextlib.redirect_stdout(sys.stderr):
        notes = vault.notes

    # Hard guard: a linter that sees nothing must fail loud, not pass silent.
    # This is the tripwire for the hidden-path indexing class of bugs.
    if not notes:
        print(
            f"wikilint: error: vault at {args.vault} indexed 0 notes — "
            "refusing to pass. Check the vault path and the parser's "
            "hidden-directory handling.",
            file=sys.stderr,
        )
        sys.exit(2)

    excludes = {e.strip("/") for e in args.exclude if e.strip("/")}
    ignored = set(args.ignore_target)
    index = build_name_index(vault)

    broken: dict[str, list[dict[str, str]]] = {}
    # redirect: note.wikilinks parses lazily and the parser prints YAML
    # warnings to stdout during the scan as well.
    with contextlib.redirect_stdout(sys.stderr):
        for note in notes:
            note_path = vault_relative(note.path, vault.path)
            if excludes and is_excluded(note_path, excludes):
                continue
            dead = []
            seen: set[str] = set()
            for link in note.wikilinks:
                # link.target is the note part only (parser splits #heading,
                # ^block and |alias). Embeds and code-fence links are already
                # excluded upstream (verified 0.4.1).
                target = (link.target or "").strip()
                if not target or target in seen or target in ignored:
                    continue  # same-page link, already reported, or ignored
                ok, reason = resolve_strict(vault, index, target)
                if not ok:
                    seen.add(target)
                    dead.append({"target": target, "reason": reason})
            if dead:
                broken[str(note_path)] = dead

    total = sum(len(v) for v in broken.values())
    # Summary always to stderr so stdout stays clean JSON when --json.
    print(f"wikilint: scanned {len(notes)} notes, "
          f"{total} broken link(s) in {len(broken)} note(s)", file=sys.stderr)

    if args.json:
        print(json.dumps(broken, indent=2))
    else:
        for path, links in broken.items():
            for item in links:
                print(f"\u2717 {path}: [[{item['target']}]] \u2014 {item['reason']}")

    sys.exit(1 if broken else 0)


if __name__ == "__main__":
    main()
