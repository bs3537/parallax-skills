#!/usr/bin/env bash
# Mirror the Claude parallax skill into Codex (~/.codex/skills/parallax), localized.
# Scripts are __file__-relative (location-independent); only *.md docs are path-localized.
# Modeled on ~/.claude/skills/valuation/tests/sync_to_codex.sh.
set -euo pipefail
SRC=/home/bhavneesh/.claude/skills/parallax
DST=/home/bhavneesh/.codex/skills/parallax
BKROOT=/home/bhavneesh/.codex/skill_restore_backups
TS="${1:-$(date +%Y%m%d_%H%M%S)}"

if [ -d "$DST" ]; then
  mkdir -p "$BKROOT"
  cp -r "$DST" "$BKROOT/parallax-$TS"
  echo "Snapshot of existing Codex skill -> $BKROOT/parallax-$TS"
fi

mkdir -p "$(dirname "$DST")"
rm -rf "$DST"
cp -r "$SRC" "$DST"
rm -rf "$DST/.git" 2>/dev/null || true
find "$DST" -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true

# Localize .claude -> .codex in docs only (scripts unchanged: run_parallax.py resolves its own tree
# root via Path(__file__).resolve().parents[3], same convention as fintwit_engine.py).
find "$DST" -name "*.md" -print0 | xargs -0 sed -i 's#/\.claude/#/.codex/#g; s#~/\.claude/#~/.codex/#g'

echo "Installed Codex skill at $DST"
echo "Localized .claude -> .codex in *.md docs; scripts are location-independent."
echo "Do NOT add to config.toml (skills are always-on by presence; an entry would DISABLE it)."
echo "Restart Codex to pick up the new skill."
