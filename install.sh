#!/usr/bin/env bash
# Install hipaa-audit as a global Claude Code skill.
# After install: `/hipaa-audit <project-path>` works in any Claude Code session.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_SRC="$REPO_DIR/skills/hipaa-audit"
SKILL_DEST="$HOME/.claude/skills/hipaa-audit"

if [[ ! -d "$SKILL_SRC" ]]; then
  echo "✗ source skill not found: $SKILL_SRC" >&2
  exit 1
fi

mkdir -p "$HOME/.claude/skills"

if [[ -e "$SKILL_DEST" || -L "$SKILL_DEST" ]]; then
  echo "→ removing existing: $SKILL_DEST"
  rm -rf "$SKILL_DEST"
fi

# Symlink so edits in the repo are picked up live.
ln -s "$SKILL_SRC" "$SKILL_DEST"

chmod +x "$SKILL_SRC/scripts/run_audit.sh" "$SKILL_SRC/scripts/"*.py 2>/dev/null || true

echo "✓ installed: $SKILL_DEST → $SKILL_SRC"
echo ""
echo "Usage in Claude Code:"
echo "  /hipaa-audit /path/to/project"
echo ""
echo "Or invoke the script directly:"
echo "  bash $SKILL_SRC/scripts/run_audit.sh /path/to/project"
echo ""
echo "Uninstall:"
echo "  bash $REPO_DIR/uninstall.sh"
