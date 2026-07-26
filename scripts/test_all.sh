#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

python3 -m py_compile \
  "$ROOT/skills/parallax-lite/scripts/run_parallax_lite.py" \
  "$ROOT/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py" \
  "$ROOT/skills/parallax/scripts/run_parallax.py"

python3 -m unittest discover -s "$ROOT/skills/parallax-lite/tests" -v
python3 -m unittest discover -s "$ROOT/skills/parallax-verified-lite/tests" -v
python3 -m unittest discover -s "$ROOT/skills/parallax/tests" -v

python3 - "$ROOT" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
for name in ("parallax-lite", "parallax-verified-lite", "parallax"):
    text = (root / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match or f"name: {name}" not in match.group(1):
        raise SystemExit(f"invalid SKILL.md frontmatter: {name}")
print("frontmatter checks: OK")
PY

python3 "$ROOT/skills/parallax-lite/scripts/run_parallax_lite.py" TEST \
  --dry-run --run-base "$TMP/lite" >/dev/null
python3 "$ROOT/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py" TEST \
  --dry-run --run-base "$TMP/verified" >/dev/null
python3 "$ROOT/skills/parallax/scripts/run_parallax.py" TEST \
  --dry-run --project-dir "$TMP/full" >/dev/null

python3 - "$TMP/full" <<'PY'
import json
import sys
from pathlib import Path

project = Path(sys.argv[1])
directories = sorted(path.name for path in project.iterdir() if path.is_dir())
if directories != ["claude_research", "codex_research"]:
    raise SystemExit(f"unexpected Full Parallax directories: {directories}")
manifest = json.loads((project / "RUN_MANIFEST.json").read_text(encoding="utf-8"))
if manifest.get("status") != "complete_both":
    raise SystemExit(f"unexpected Full Parallax status: {manifest.get('status')}")
if manifest.get("topology") != "dual_gauntlet_fast_no_merge":
    raise SystemExit(f"unexpected Full Parallax topology: {manifest.get('topology')}")
for token in ("merged", "verdict", "claim_matrix", "final_answer"):
    if any(token in path.name.lower() for path in project.rglob("*")):
        raise SystemExit(f"forbidden Full Parallax artifact token: {token}")
print("full topology checks: OK")
PY

"$ROOT/install.sh" --dest "$TMP/install/skills"
test -x "$TMP/install/skills/parallax-lite/scripts/run_parallax_lite.py"
test -x "$TMP/install/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py"
test -x "$TMP/install/skills/parallax/scripts/run_parallax.py"
python3 "$TMP/install/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py" TEST \
  --dry-run --run-base "$TMP/installed-smoke" >/dev/null
python3 "$TMP/install/skills/parallax/scripts/run_parallax.py" TEST \
  --dry-run --project-dir "$TMP/installed-full-smoke" >/dev/null

HOME="$TMP/both-home" CODEX_HOME="$TMP/both-codex" \
  "$ROOT/install.sh" --surface both >/dev/null
test -x "$TMP/both-home/.claude/skills/parallax/scripts/run_parallax.py"
test -x "$TMP/both-codex/skills/parallax/scripts/run_parallax.py"
diff -qr --exclude='__pycache__' --exclude='*.pyc' \
  "$TMP/both-home/.claude/skills/parallax" "$TMP/both-codex/skills/parallax" >/dev/null

mkdir -p "$TMP/refusal-home/.claude/skills/parallax"
touch "$TMP/refusal-home/.claude/skills/parallax/user-owned"
set +e
HOME="$TMP/refusal-home" CODEX_HOME="$TMP/refusal-codex" \
  "$ROOT/install.sh" --surface both >/dev/null 2>&1
refusal_status=$?
set -e
test "$refusal_status" -eq 4
test -f "$TMP/refusal-home/.claude/skills/parallax/user-owned"
test ! -e "$TMP/refusal-codex/skills/parallax"

echo "all repository tests: OK"
