# Agent Instructions for obsidian-wikilint

## Tool Purpose
This is a strict, exact-resolution linter for Obsidian `[[wikilinks]]`. 
It DOES NOT auto-fix. It only reports.

## How to use in a CI/Pipeline/Agent loop
1. Run `wikilint /path/to/vault --json`.
2. If exit code is `0`, the vault is clean. Proceed with commit.
3. If exit code is `1`, parse the JSON output.
4. Use your native file-editing tools to manually fix the exact `line` and `column` reported in the JSON.
5. Re-run the linter to verify the fix.

Note: if your runner exports `PYTHONPATH` (agent frameworks do), clear it for this tool —
`env -u PYTHONPATH wikilint /path/to/vault …` — because a stale entry makes the interpreter
import foreign modules and the linter fails on every run for an unrelated reason.

## Constraints & Deny Rules
- NEVER use `sed` or blind regex to replace broken links across the whole vault. Obsidian aliases and block references will be corrupted.
- NEVER bypass the pre-commit hook with `--no-verify` if this tool fails. Fix the links instead.