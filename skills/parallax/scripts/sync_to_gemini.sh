#!/usr/bin/env bash
# Mirror the Claude parallax skill into agy/Gemini (~/.gemini/skills/parallax), localized.
# Same model as sync_to_codex.sh: scripts are __file__-relative; only *.md docs are path-localized.
# Modeled on ~/.claude/skills/valuation/tests/sync_to_gemini.sh.
set -euo pipefail
SRC=/home/bhavneesh/.claude/skills/parallax
DST=/home/bhavneesh/.gemini/skills/parallax
BKROOT=/home/bhavneesh/.gemini/skill_restore_backups
TS="${1:-$(date +%Y%m%d_%H%M%S)}"

if [ -d "$DST" ]; then
  mkdir -p "$BKROOT"
  cp -r "$DST" "$BKROOT/parallax-$TS"
  echo "Snapshot of existing Gemini skill -> $BKROOT/parallax-$TS"
fi

mkdir -p "$(dirname "$DST")"
rm -rf "$DST"
cp -r "$SRC" "$DST"
rm -rf "$DST/.git" 2>/dev/null || true
find "$DST" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$DST" -name "*.md" -print0 | xargs -0 sed -i 's#/\.claude/#/.gemini/#g; s#~/\.claude/#~/.gemini/#g'

echo "Installed agy/Gemini skill at $DST"
echo "Localized .claude -> .gemini in *.md docs; scripts are location-independent."
echo "Add a one-line trigger to ~/.gemini/GEMINI.md (mirror the search-as-code reference)."
