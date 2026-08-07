# obsidian-wikilint

![Tests](https://github.com/Scan-law4/obsidian-wikilint/actions/workflows/test.yml/badge.svg)

Check an Obsidian-compatible markdown vault for broken `[[wikilinks]]`.
Exit 1 on failure — ready for pre-commit hooks and CI.

Strict resolution only: no fuzzy matching, so a typo like `[[peper]]`
is flagged instead of silently resolving to `pepper.md`.

## Install

```bash
pip install git+https://github.com/Scan-law4/obsidian-wikilint.git
```

Requirements: Python ≥3.12 (upstream `obsidianmd-parser` constraint), `obsidianmd-parser` ≥0.4.1,<0.5.

## Usage

```bash
wikilint /path/to/vault                    # check all notes
wikilint /path/to/vault --exclude _archive # skip directories
wikilint /path/to/vault --json             # machine-readable output
wikilint /path/to/vault --ignore-target pattern  # ignore intentional links
```

Exit codes: `0` clean, `1` broken links found, `2` environment error
(vault missing or indexed 0 notes — the linter fails loud, never
passes silently).

## Pre-commit hook

```yaml
repos:
  - repo: https://github.com/Scan-law4/obsidian-wikilint
    rev: v0.1.0
    hooks:
      - id: obsidian-wikilint
        args: ["path/to/vault"]
```

Note: you must provide the vault path via `args`. `pass_filenames: false`
means the hook lints the full vault on any `.md` change. For large vaults,
consider a dedicated CI job instead.

### After installing the hook: baseline pass

When you first install any pre-commit hook, run it against your whole
repo and commit the fixes BEFORE normal commits:

```bash
wikilint path/to/vault        # checks for broken [[wikilinks]] (no auto-fix)
# → Fix every reported link manually, then:
git add . && git commit -m "chore: baseline lint pass"
```

Skipping this step means notes committed before the hook carry invisible
violations. The first commit touching those old notes is rejected — even
though it's no dirtier than HEAD.

## Known upstream quirks handled

obsidian-wikilint wraps [`obsidianmd-parser`](https://codeberg.org/paddyd/obsidianmd-parser)
with workarounds for three known issues:

| Issue | Our fix |
|-------|---------|
| Vault silently indexes 0 notes under dot-prefixed paths | `vault_compat.py` — patches private method to respect all directories |
| `find_broken_links()` uses fuzzy matching (wrong for integrity checks) | `resolve_strict()` — exact `get_note()` resolution, no tolerance |
| Library writes `print()` calls to stdout, corrupting JSON output | `cli.py` — `redirect_stdout` to stderr, transparent mode bypass |

These are workarounds, not upstream fixes. Upstream issues pending.
