# Changelog

## 0.1.0 (2026-08-05)

Initial release — exact-resolution Obsidian wikilink linter.

- Strict `[[wikilink]]` resolution via `obsidianmd-parser` vault graph
- No fuzzy matching — typos are flagged, not silently resolved
- Pre-commit hook ready (`.pre-commit-hooks.yaml` included)
- `--exclude` glob patterns, `--json` output, `--ignore-target` for intentional links
- Tested clean against 957-note vault (0 broken, exit 0)
- Installed via `pip install git+https://github.com/Scan-law4/obsidian-wikilint.git`
