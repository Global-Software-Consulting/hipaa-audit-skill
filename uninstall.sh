#!/usr/bin/env bash
# Uninstall hipaa-audit skill from Claude Code global skills.

set -euo pipefail

SKILL_DEST="$HOME/.claude/skills/hipaa-audit"

if [[ -L "$SKILL_DEST" ]]; then
  rm "$SKILL_DEST"
  echo "✓ removed symlink: $SKILL_DEST"
elif [[ -d "$SKILL_DEST" ]]; then
  rm -rf "$SKILL_DEST"
  echo "✓ removed directory: $SKILL_DEST"
else
  echo "→ nothing to remove at: $SKILL_DEST"
fi
