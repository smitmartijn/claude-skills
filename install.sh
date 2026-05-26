#!/usr/bin/env bash
set -euo pipefail

REPO="smitmartijn/claude-skills"
BRANCH="main"
SKILLS_DIR="$HOME/.claude/skills"

usage() {
  echo "Usage: $0 <skill-name> [skill-name ...] | --all | --list"
  echo ""
  echo "Install Claude Code skills from github.com/$REPO"
  echo ""
  echo "Options:"
  echo "  --all    Install all available skills"
  echo "  --list   List available skills"
  echo "  --help   Show this help"
  exit 1
}

fetch_archive() {
  local tmpdir
  tmpdir=$(mktemp -d)
  curl -sL "https://github.com/$REPO/archive/$BRANCH.tar.gz" | tar -xz -C "$tmpdir"
  ARCHIVE_DIR="$tmpdir"/*/
  echo "$tmpdir"
}

available_skills() {
  local tmpdir
  tmpdir=$(fetch_archive)
  for dir in "$tmpdir"/*/*/; do
    local name
    name=$(basename "$dir")
    if [ -f "$dir/SKILL.md" ]; then
      echo "$name"
    fi
  done
  rm -rf "$tmpdir"
}

install_skill() {
  local skill="$1"
  local src="$ARCHIVE_DIR/$skill"
  local dest="$SKILLS_DIR/$skill"

  if [ ! -d "$src" ] || [ ! -f "$src/SKILL.md" ]; then
    echo "error: skill '$skill' not found in repo" >&2
    return 1
  fi

  rm -rf "$dest"
  mkdir -p "$dest"
  cp -R "$src"/* "$dest"/
  local file_count
  file_count=$(find "$dest" -type f | wc -l | tr -d ' ')
  echo "installed: $skill -> $dest/ ($file_count files)"
}

if [ $# -eq 0 ]; then
  usage
fi

case "$1" in
  --help|-h)
    usage
    ;;
  --list)
    echo "Available skills:"
    available_skills | while read -r skill; do
      echo "  $skill"
    done
    ;;
  --all)
    tmpdir=$(fetch_archive)
    trap 'rm -rf "$tmpdir"' EXIT
    for dir in "$tmpdir"/*/*/; do
      skill=$(basename "$dir")
      if [ -f "$dir/SKILL.md" ]; then
        install_skill "$skill"
      fi
    done
    ;;
  *)
    tmpdir=$(fetch_archive)
    trap 'rm -rf "$tmpdir"' EXIT
    for skill in "$@"; do
      install_skill "$skill"
    done
    ;;
esac
