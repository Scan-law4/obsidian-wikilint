#!/bin/bash
# Control-vault test battery for obsidian-wikilint. Writes only under /tmp.
set -u
# Resolve the interpreter and the tool RELATIVE TO THIS REPO (decided 2026-09-27), so the battery
# is portable by construction and not by machine: `tests/../.venv`. The PATH fallback below still
# covers CI runners and any checkout without a local venv.
HERE=$(cd "$(dirname "$0")" && pwd)
PY="$HERE/../.venv/bin/python"
WL="$HERE/../.venv/bin/wikilint"
# Portability: this battery runs on this machine AND in GitHub Actions CI.
# Local venv paths exist here; on a runner they don't — fall back to PATH.
# Override explicitly (PY=/usr/bin/python3 WL=... bash tests/control_battery.sh)
# to pin a specific interpreter/binary.
[ -x "$PY" ] || PY=$(command -v python3 || echo python3)
[ -x "$WL" ] || WL=$(command -v wikilint || echo wikilint)
echo "battery: PY=$PY WL=$WL"
T=$(mktemp -d /tmp/wikilint_battery_XXXX)
pass=0; fail=0
check() { # name expected_exit actual_exit
  if [ "$2" -eq "$3" ]; then echo "PASS: $1 (exit $3)"; pass=$((pass+1));
  else echo "FAIL: $1 (expected $2, got $3)"; fail=$((fail+1)); fi
}

# Vault fixture
mkdir -p "$T/vault/agents" "$T/vault/_archive" "$T/vault/.obsidian"
cat > "$T/vault/agents/pepper.md" <<'EOF'
---
aliases: [Pep]
---
# Pepper
EOF
echo "# House" > "$T/vault/agents/house.md"
echo "junk" > "$T/vault/.obsidian/app.json"
echo "archived broken: [[gone_page]]" > "$T/vault/_archive/old.md"
cat > "$T/vault/index.md" <<'EOF'
valid path: [[agents/pepper]]
valid bare: [[house]]
valid alias-display: [[agents/pepper|display text]]
valid fragment: [[agents/pepper#Section]]
same page: [[#local]]
code fence:
```
[[not_a_link]]
```
EOF

# 1. clean vault (archive excluded) -> 0
"$WL" "$T/vault" --exclude _archive >/dev/null 2>&1
check "clean vault exits 0" 0 $?

# 2. no exclude -> archive's [[gone_page]] breaks it -> 1
"$WL" "$T/vault" >/dev/null 2>&1
check "archive included exits 1" 1 $?

# 3. add typo link -> 1 (fuzzy would pass this)
echo "typo: [[peper]]" > "$T/vault/typo.md"
"$WL" "$T/vault" --exclude _archive >/dev/null 2>&1
check "typo [[peper]] flagged" 1 $?
"$WL" "$T/vault" --exclude _archive 2>/dev/null | grep -q 'peper'
check "typo named in output" 0 $?
rm "$T/vault/typo.md"

# 4. broken link -> 1
echo "broken: [[xyz_nonexistent]]" > "$T/vault/broken.md"
"$WL" "$T/vault" --exclude _archive >/dev/null 2>&1
check "broken link exits 1" 1 $?

# 5. --json validity
"$WL" "$T/vault" --exclude _archive --json 2>/dev/null | "$PY" -m json.tool >/dev/null
check "--json is valid JSON" 0 $?
rm "$T/vault/broken.md"

# 6. missing vault path -> 2
"$WL" "$T/nope" >/dev/null 2>&1
check "missing vault exits 2" 2 $?

# 7. 0-notes guard -> 2 (empty dir)
mkdir "$T/empty"
"$WL" "$T/empty" >/dev/null 2>&1
check "0-note vault exits 2" 2 $?

# 8. ambiguous bare name -> 1 with reason
echo "# dup" > "$T/vault/dup.md"
echo "# dup" > "$T/vault/agents/dup.md"
echo "ambiguous: [[dup]]" > "$T/vault/amb.md"
"$WL" "$T/vault" --exclude _archive 2>/dev/null | grep -q 'ambiguous'
check "ambiguous bare name reported" 0 $?
rm "$T/vault/dup.md" "$T/vault/agents/dup.md" "$T/vault/amb.md"

# 9. python -m entry point
"$PY" -m obsidian_wikilint "$T/vault" --exclude _archive >/dev/null 2>&1
check "python -m works, clean exit 0" 0 $?

# 10. alias limitation is DOCUMENTED behavior: [[Pep]] flagged broken
echo "alias link: [[Pep]]" > "$T/vault/aliaslink.md"
"$WL" "$T/vault" --exclude _archive >/dev/null 2>&1
check "frontmatter alias flagged (known limitation)" 1 $?
rm "$T/vault/aliaslink.md"

echo
echo "passed=$pass failed=$fail"
rm -rf "$T"
exit $fail
