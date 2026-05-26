#!/usr/bin/env bash
set -euo pipefail

REPO="smitmartijn/claude-skills"
BRANCH="main"
BASE_URL="https://raw.githubusercontent.com/$REPO/$BRANCH"
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

available_skills() {
  curl -sL "https://api.github.com/repos/$REPO/contents?ref=$BRANCH" \
    | grep '"name"' \
    | grep -v -E '"(README|install|LICENSE|\.)' \
    | sed 's/.*"name": "//;s/".*//'
}

install_skill() {
  local skill="$1"
  local url="$BASE_URL/$skill/SKILL.md"
  local dest="$SKILLS_DIR/$skill"

  local http_code
  http_code=$(curl -sL -o /dev/null -w '%{http_code}' "$url")
  if [ "$http_code" != "200" ]; then
    echo "error: skill '$skill' not found in repo" >&2
    return 1
  fi

  mkdir -p "$dest"
  curl -sL "$url" -o "$dest/SKILL.md"
  echo "installed: $skill -> $dest/SKILL.md"
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
    available_skills | while read -r skill; do
      install_skill "$skill"
    done
    ;;
  *)
    for skill in "$@"; do
      install_skill "$skill"
    done
    ;;
esac
