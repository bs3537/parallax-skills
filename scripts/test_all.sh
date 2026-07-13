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
  --dry-run --run-base "$TMP/full" >/dev/null

"$ROOT/install.sh" --dest "$TMP/install/skills"
test -x "$TMP/install/skills/parallax-lite/scripts/run_parallax_lite.py"
test -x "$TMP/install/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py"
test -x "$TMP/install/skills/parallax/scripts/run_parallax.py"
python3 "$TMP/install/skills/parallax-verified-lite/scripts/run_parallax_verified_lite.py" TEST \
  --dry-run --run-base "$TMP/installed-smoke" >/dev/null

echo "all repository tests: OK"
