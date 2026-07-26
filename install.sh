#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FORCE=0
DRY_RUN=0
SURFACE="codex"
CUSTOM_DEST=""
SKILLS=(parallax-lite parallax-verified-lite parallax)

usage() {
  cat <<'EOF'
Usage: ./install.sh [--surface codex|claude|both] [--force] [--dry-run]
       ./install.sh --dest /path/to/skills [--force] [--dry-run]
EOF
}

while (($#)); do
  case "$1" in
    --surface)
      shift
      [[ $# -gt 0 ]] || { echo "install: --surface requires a value" >&2; exit 2; }
      SURFACE="$1"
      ;;
    --dest)
      shift
      [[ $# -gt 0 ]] || { echo "install: --dest requires a path" >&2; exit 2; }
      CUSTOM_DEST="$1"
      ;;
    --force) FORCE=1 ;;
    --dry-run) DRY_RUN=1 ;;
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

if [[ -n "$CUSTOM_DEST" ]]; then
  DESTS=("$CUSTOM_DEST")
else
  case "$SURFACE" in
    codex) DESTS=("${CODEX_HOME:-$HOME/.codex}/skills") ;;
    claude) DESTS=("$HOME/.claude/skills") ;;
    both) DESTS=("$HOME/.claude/skills" "${CODEX_HOME:-$HOME/.codex}/skills") ;;
    *)
      echo "install: --surface must be codex, claude, or both" >&2
      exit 2
      ;;
  esac
fi

# Preflight every destination before changing any destination.
for dest in "${DESTS[@]}"; do
  existing=()
  for skill in "${SKILLS[@]}"; do
    [[ -e "$dest/$skill" ]] && existing+=("$skill")
  done
  if ((${#existing[@]})) && ((FORCE == 0)); then
    echo "install: refusing to overwrite existing skills in $dest: ${existing[*]}" >&2
    echo "Re-run with --force to back them up and install." >&2
    exit 4
  fi
done

if ((DRY_RUN)); then
  for dest in "${DESTS[@]}"; do
    echo "Would install to: $dest"
    printf '  %s\n' "${SKILLS[@]}"
  done
  exit 0
fi

timestamp="$(date -u +%Y%m%d_%H%M%S)"
for dest in "${DESTS[@]}"; do
  mkdir -p "$dest"
  stage="$(mktemp -d "$dest/.parallax-skills-stage.XXXXXX")"

  for skill in "${SKILLS[@]}"; do
    cp -a "$ROOT/skills/$skill" "$stage/$skill"
    find "$stage/$skill" -type d -name __pycache__ -prune -exec rm -rf {} +
    find "$stage/$skill" -type f -name '*.pyc' -delete
  done

  runtime_home="$(dirname "$dest")"
  backup_root="$runtime_home/skill-backups/$timestamp"
  existing=()
  for skill in "${SKILLS[@]}"; do
    [[ -e "$dest/$skill" ]] && existing+=("$skill")
  done
  if ((${#existing[@]})); then
    mkdir -p "$backup_root"
    for skill in "${existing[@]}"; do
      mv "$dest/$skill" "$backup_root/$skill"
    done
    echo "Backed up existing skills to: $backup_root"
  fi

  for skill in "${SKILLS[@]}"; do
    mv "$stage/$skill" "$dest/$skill"
    echo "Installed: $dest/$skill"
  done
  rmdir "$stage"
done

echo "Installation complete."
if [[ -z "$CUSTOM_DEST" ]]; then
  case "$SURFACE" in
    codex) echo "Restart Codex to reload skill metadata." ;;
    claude) echo "Restart Claude Code to reload skill metadata." ;;
    both) echo "Restart Claude Code and Codex to reload skill metadata." ;;
  esac
fi
