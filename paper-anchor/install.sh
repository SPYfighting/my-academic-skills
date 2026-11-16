#!/usr/bin/env bash
# Install or update the user-level skill with bash install.sh.
# Use bash install.sh --hook DIR to install the optional Git hook.
set -euo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)"

if [ "${1:-}" = "--hook" ]; then
  DIR="${2:-}"
  if [ -z "$DIR" ] || ! ROOT=$(git -C "$DIR" rev-parse --show-toplevel 2>/dev/null); then
    echo "Usage: bash install.sh --hook <git project directory>" >&2
    exit 2
  fi
  cd "$ROOT"
  if git config --get core.hooksPath >/dev/null; then
    echo "The project sets core.hooksPath. Merge the skill's hooks/pre-commit into the configured hook." >&2
    exit 1
  fi
  HOOKS=$(git rev-parse --git-path hooks)
  TARGET="$HOOKS/pre-commit"
  if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
    echo "The pre-commit hook already exists. Merge the skill's hooks/pre-commit manually." >&2
    exit 1
  fi
  mkdir -p "$HOOKS"
  cp "$SRC/hooks/pre-commit" "$TARGET"
  chmod +x "$TARGET"
  echo "Installed the pre-commit hook."
  exit 0
fi

# Install the shared user-level copy.
DEST="$HOME/.agents/skills/paper-anchor"
mkdir -p "$DEST"
cp -R "$SRC"/{SKILL.md,README.md,LICENSE,NOTICE.md,install.sh,bootstrap,examples,hooks,scripts,templates,tests} "$DEST/"
echo "Installed ~/.agents/skills/paper-anchor."

# Claude Code uses a separate location. Prefer a symlink to the shared copy.
mkdir -p "$HOME/.claude/skills"
LINK="$HOME/.claude/skills/paper-anchor"
if [ -L "$LINK" ] || [ ! -e "$LINK" ]; then
  rm -f "$LINK"
  ln -s "$DEST" "$LINK" 2>/dev/null || cp -r "$DEST" "$LINK"
else
  cp -R "$DEST/." "$LINK/"
fi
echo "Installed ~/.claude/skills/paper-anchor."

echo ""
echo "Enable the skill in a project by adding bootstrap/snippet.md to its agent rules."
