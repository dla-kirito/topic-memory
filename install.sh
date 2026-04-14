#!/bin/bash
# Topic Memory — 一键安装脚本
# https://github.com/dla-kirito/topic-memory
#
# 使用方式：
#   curl -sSL https://raw.githubusercontent.com/dla-kirito/topic-memory/main/install.sh | bash

set -e

REPO_URL="https://raw.githubusercontent.com/dla-kirito/topic-memory/main"
CLAUDE_DIR="$HOME/.claude"
HOOKS_DIR="$CLAUDE_DIR/hooks"
SKILLS_DIR="$CLAUDE_DIR/skills"
SETTINGS="$CLAUDE_DIR/settings.json"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "Installing Topic Memory for Claude Code..."
echo ""

# 检查已安装
if [ -f "$HOOKS_DIR/pre-compact-inject.sh" ] && [ -f "$HOOKS_DIR/post-compact-save-topic.py" ]; then
  echo -e "${YELLOW}Topic Memory is already installed.${NC}"
  read -p "Reinstall? (y/N) " confirm
  if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
    echo "Cancelled."
    exit 0
  fi
fi

# 创建目录
mkdir -p "$HOOKS_DIR"
mkdir -p "$SKILLS_DIR/recall/scripts"
mkdir -p "$SKILLS_DIR/note"
mkdir -p "$SKILLS_DIR/install-topic-memory"

# 下载 hooks
echo "→ Installing hooks..."
curl -sSL "$REPO_URL/hooks/pre-compact-inject.sh" -o "$HOOKS_DIR/pre-compact-inject.sh"
chmod +x "$HOOKS_DIR/pre-compact-inject.sh"
curl -sSL "$REPO_URL/hooks/post-compact-save-topic.py" -o "$HOOKS_DIR/post-compact-save-topic.py"

# 下载 skills
echo "→ Installing skills..."
curl -sSL "$REPO_URL/skills/recall/SKILL.md" -o "$SKILLS_DIR/recall/SKILL.md"
curl -sSL "$REPO_URL/skills/recall/scripts/search_topics.py" -o "$SKILLS_DIR/recall/scripts/search_topics.py"
mkdir -p "$SKILLS_DIR/note"
curl -sSL "$REPO_URL/skills/note/SKILL.md" -o "$SKILLS_DIR/note/SKILL.md"
curl -sSL "$REPO_URL/skills/install-topic-memory/SKILL.md" -o "$SKILLS_DIR/install-topic-memory/SKILL.md"

# 更新 settings.json
echo "→ Updating settings.json..."
python3 - "$SETTINGS" << 'EOF'
import json, sys, os
from pathlib import Path

settings_path = Path(sys.argv[1])
settings = {}
if settings_path.exists():
    try:
        settings = json.loads(settings_path.read_text())
    except Exception:
        pass

hooks = settings.setdefault("hooks", {})

def add_hook(event, command):
    entries = hooks.setdefault(event, [])
    for entry in entries:
        for h in entry.get("hooks", []):
            if h.get("command") == command:
                return  # already exists
    entries.append({
        "matcher": "",
        "hooks": [{"type": "command", "command": command}]
    })

add_hook("PreCompact", "bash ~/.claude/hooks/pre-compact-inject.sh")
add_hook("PostCompact", "python3 ~/.claude/hooks/post-compact-save-topic.py")

settings_path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n")
print("settings.json updated.")
EOF

echo ""
echo -e "${GREEN}✅ Topic Memory installed successfully!${NC}"
echo ""
echo "Files created:"
echo "  $HOOKS_DIR/pre-compact-inject.sh"
echo "  $HOOKS_DIR/post-compact-save-topic.py"
echo "  $SKILLS_DIR/recall/SKILL.md"
echo "  $SKILLS_DIR/recall/scripts/search_topics.py"
echo "  $SKILLS_DIR/note/SKILL.md"
echo ""
echo "Usage:"
echo "  Automatic : topic is saved on every compact"
echo "  Recall    : /recall <keyword>  in Claude Code"
echo "  Note      : /note              save progress immediately (no compact needed)"
echo "              /note <name>       update a specific topic"
echo ""
echo -e "${YELLOW}Restart Claude Code to activate.${NC}"
echo ""
