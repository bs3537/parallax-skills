#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="${CODEX_HOME:-$HOME/.codex}/skills"
FORCE=0
DRY_RUN=0
SKILLS=(parallax-lite parallax-verified-lite parallax)

usage() {
  echo "Usage: ./install.sh [--force] [--dry-run] [--dest /path/to/skills]"
}

while (($#)); do
  case "$1" in
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    --dest)
      shift
      [[ $# -gt 0 ]] || { echo "install: --dest requires a path" >&2; exit 2; }
      DEST="$1"
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "install: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
  shift
done

for skill in "${SKILLS[@]}"; do
  [[ -f "$ROOT/skills/$skill/SKILL.md" ]] || {
    echo "install: missing skills/$skill/SKILL.md" >&2
    exit 3
  }
done

existing=()
for skill in "${SKILLS[@]}"; do
  [[ -e "$DEST/$skill" ]] && existing+=("$skill")
done
if ((${#existing[@]})) && ((FORCE == 0)); then
  echo "install: refusing to overwrite existing skills: ${existing[*]}" >&2
  echo "Re-run with --force to back them up and install." >&2
  exit 4
fi

if ((DRY_RUN)); then
  echo "Would install to: $DEST"
  printf '  %s\n' "${SKILLS[@]}"
  ((${#existing[@]})) && echo "Would back up: ${existing[*]}"
  exit 0
fi

mkdir -p "$DEST"
stage="$(mktemp -d "$DEST/.parallax-skills-stage.XXXXXX")"
trap 'rm -rf "$stage"' EXIT

for skill in "${SKILLS[@]}"; do
  cp -a "$ROOT/skills/$skill" "$stage/$skill"
  find "$stage/$skill" -type d -name __pycache__ -prune -exec rm -rf {} +
  find "$stage/$skill" -type f -name '*.pyc' -delete
done

backup_root="${CODEX_HOME:-$HOME/.codex}/skill-backups/$(date -u +%Y%m%d_%H%M%S)"
if ((${#existing[@]})); then
  mkdir -p "$backup_root"
  for skill in "${existing[@]}"; do
    mv "$DEST/$skill" "$backup_root/$skill"
  done
  echo "Backed up existing skills to: $backup_root"
fi

for skill in "${SKILLS[@]}"; do
  mv "$stage/$skill" "$DEST/$skill"
  echo "Installed: $DEST/$skill"
done

echo "Installation complete. Restart Codex to reload skill metadata."
