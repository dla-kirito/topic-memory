---
name: install-topic-memory
description: 一键安装 Topic Memory 系统：自动配置 PreCompact/PostCompact hooks 和 /recall skill，让每次 compact 自动保存任务上下文，可用 /recall 按需召回。当用户说"安装 topic memory"、"install topic memory"、"/install-topic-memory"时触发。
---

# Install Topic Memory

一键安装 Topic Memory 系统。安装完成后，每次 compact 会自动提取并保存任务上下文到 topic 文件，可用 `/recall` 按需召回。

## 工作流

### Step 1 — 检查已安装状态

检查以下文件是否已存在：
- `~/.claude/hooks/pre-compact-inject.sh`
- `~/.claude/hooks/post-compact-save-topic.py`
- `~/.claude/skills/recall/SKILL.md`

若均已存在，询问用户是否重新安装（覆盖）。若用户取消，终止安装。

### Step 2 — 创建目录

```bash
mkdir -p ~/.claude/hooks
mkdir -p ~/.claude/skills/recall/scripts
mkdir -p ~/.claude/skills/install-topic-memory
```

### Step 3 — 写入 PreCompact hook

创建文件 `~/.claude/hooks/pre-compact-inject.sh`，写入以下**完整内容**：

```
#!/bin/bash
# PreCompact hook: 向 compact 提示词注入结构化提取指令
# Claude 在生成压缩摘要时会附带输出 topic-json 块
# PostCompact hook 随后解析该块并写入 topic 文件

cat << 'INSTRUCTIONS'
在完成对话压缩摘要后，请在摘要末尾额外附加一个 topic-json 块，用于持久化保存本次任务的关键上下文。格式如下：

```topic-json
{
  "topic_slug": "英文短横线连接的标识符，如 react-performance",
  "description": "一句话描述当前任务（中文，50字以内）",
  "task_goal": "任务的核心目标是什么",
  "decisions": ["关键决策1（含原因）", "关键决策2（含原因）"],
  "preferences": ["观察到的用户编码/工作偏好1", "偏好2"],
  "pitfalls": ["踩过的坑或失败的尝试"],
  "current_status": "当前进度和下一步"
}
```

注意：如果对话内容不涉及具体任务（如纯聊天），可以省略此块。
INSTRUCTIONS

exit 0
```

然后执行：`chmod +x ~/.claude/hooks/pre-compact-inject.sh`

### Step 4 — 写入 PostCompact hook

创建文件 `~/.claude/hooks/post-compact-save-topic.py`，写入以下**完整内容**：

```python
#!/usr/bin/env python3
"""
PostCompact hook: 从 compactSummary 解析 topic-json 块，写入 topic 文件和索引。
任何异常都静默处理，不阻断 compact 后续流程。
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def get_topics_dir(transcript_path: str) -> Path:
    project_dir = Path(transcript_path).expanduser().parent
    return project_dir / "topics"


def parse_topic_json(summary: str):
    pattern = r"```topic-json\s*\n(.*?)\n```"
    match = re.search(pattern, summary, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def slugify(s: str) -> str:
    s = re.sub(r"[^\w-]", "-", s.lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "untitled"


def read_frontmatter(content: str) -> dict:
    fm = {}
    if not content.startswith("---"):
        return fm
    end = content.find("\n---", 3)
    if end == -1:
        return fm
    block = content[3:end].strip()
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",")]
            fm[key] = [i for i in items if i]
        else:
            fm[key] = val.strip('"').strip("'")
    return fm


def parse_list_from_text(text: str) -> list:
    items = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def build_content(slug, description, sessions, date, task_goal, decisions, preferences, pitfalls, current_status) -> str:
    sessions_str = "[" + ", ".join(sessions) + "]"
    lines = ["---", f"topic: {slug}", f"description: {description}",
             f"sessions: {sessions_str}", f"date: {date}", "---", ""]
    if task_goal:
        lines += ["## 任务目标", task_goal, ""]
    if decisions:
        lines += ["## 关键决策"] + [f"- {d}" for d in decisions] + [""]
    if preferences:
        lines += ["## 用户偏好"] + [f"- {p}" for p in preferences] + [""]
    if pitfalls:
        lines += ["## 踩坑记录"] + [f"- {p}" for p in pitfalls] + [""]
    if current_status:
        lines += ["## 当前状态", current_status, ""]
    return "\n".join(lines)


def write_topic_file(topics_dir: Path, data: dict, session_id: str):
    slug = slugify(data.get("topic_slug", "untitled"))
    topic_file = topics_dir / f"{slug}.md"
    today = datetime.now().strftime("%Y-%m-%d")

    if topic_file.exists():
        existing = topic_file.read_text(encoding="utf-8")
        fm = read_frontmatter(existing)
        sessions = fm.get("sessions", [])
        if isinstance(sessions, str):
            sessions = [sessions]
        if session_id and session_id not in sessions:
            sessions.append(session_id)

        body_start = existing.find("\n---", 3)
        body_start = existing.find("\n", body_start + 1) + 1 if body_start != -1 else 0
        body = existing[body_start:]

        def extract_section(text, heading):
            m = re.search(rf"## {heading}\n(.*?)(?=\n##|\Z)", text, re.DOTALL)
            return m.group(1) if m else ""

        existing_decisions = parse_list_from_text(extract_section(body, "关键决策"))
        existing_pitfalls = parse_list_from_text(extract_section(body, "踩坑记录"))
        new_decisions = existing_decisions + [d for d in data.get("decisions", []) if d not in extract_section(body, "关键决策")]
        new_pitfalls = existing_pitfalls + [p for p in data.get("pitfalls", []) if p not in extract_section(body, "踩坑记录")]

        content = build_content(
            slug=slug,
            description=data.get("description", fm.get("description", "")),
            sessions=sessions, date=today,
            task_goal=data.get("task_goal", ""),
            decisions=new_decisions,
            preferences=data.get("preferences", []),
            pitfalls=new_pitfalls,
            current_status=data.get("current_status", ""),
        )
    else:
        sessions = [session_id] if session_id else []
        content = build_content(
            slug=slug, description=data.get("description", ""),
            sessions=sessions, date=today,
            task_goal=data.get("task_goal", ""),
            decisions=data.get("decisions", []),
            preferences=data.get("preferences", []),
            pitfalls=data.get("pitfalls", []),
            current_status=data.get("current_status", ""),
        )

    topic_file.write_text(content, encoding="utf-8")
    return slug, data.get("description", "")


def update_index(topics_dir: Path, slug: str, description: str):
    index_file = topics_dir / "TOPICS.md"
    entry = f"- [{slug}]({slug}.md) — {description}"
    lines = index_file.read_text(encoding="utf-8").splitlines() if index_file.exists() else []
    slug_prefix = f"- [{slug}]"
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(slug_prefix):
            new_lines.append(entry)
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.insert(0, entry)
    index_file.write_text("\n".join(new_lines[:200]) + "\n", encoding="utf-8")


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)
        inp = json.loads(raw)
        summary = inp.get("compactSummary", "")
        transcript_path = inp.get("transcript_path", "")
        session_id = inp.get("session_id", "")
        if not summary or not transcript_path:
            sys.exit(0)
        data = parse_topic_json(summary)
        if not data:
            sys.exit(0)
        topics_dir = get_topics_dir(transcript_path)
        topics_dir.mkdir(parents=True, exist_ok=True)
        slug, description = write_topic_file(topics_dir, data, session_id)
        update_index(topics_dir, slug, description)
        print(f"[Topic Memory] 已保存 topic: {slug}")
    except Exception:
        sys.exit(0)


if __name__ == "__main__":
    main()
```

### Step 5 — 写入 recall skill

创建文件 `~/.claude/skills/recall/SKILL.md`，写入以下**完整内容**：

```
---
name: recall
description: 召回历史 topic 上下文注入当前 session。当用户说"召回"、"/recall"、"找一下之前"、"上次做过"、"之前的任务"、"记得之前"时触发。
---

# Topic Memory Recall

从当前项目的 topic 历史中找到相关上下文，注入当前 session。

## 定位脚本

SCRIPT_DIR="$(find ~/.claude ~/Library/Caches/coco/plugins -path '*/recall/scripts/search_topics.py' -print -quit 2>/dev/null | xargs dirname 2>/dev/null)"

## 工作流

### Step 1 — 确定 topics 目录

CWD=$(pwd)
SANITIZED=$(echo "$CWD" | sed 's|/|-|g')
TOPICS_DIR="$HOME/.claude/projects/${SANITIZED}/topics"

若 topics 目录不存在，告知用户"当前项目还没有保存的 topic，完成一次 compact 后会自动生成"，结束。

### Step 2 — 搜索相关 topic

python3 "$SCRIPT_DIR/search_topics.py" --topics-dir "$TOPICS_DIR" --query "<用户的关键词>"

无关键词时省略 --query，返回最近修改的 5 个。

### Step 3 — 展示候选并确认

读取每个 topic 文件的 frontmatter，展示 description 和 date 供用户选择。

### Step 4 — 注入选定 topic

读取用户选定的 topic 文件完整内容，展示并说明："已召回 topic [xxx]，以下是上次任务的关键上下文。"
```

### Step 6 — 写入 search_topics.py

创建文件 `~/.claude/skills/recall/scripts/search_topics.py`，写入以下**完整内容**：

```python
#!/usr/bin/env python3
"""search_topics.py — 搜索 topics 目录中的相关 topic 文件"""

import argparse
import re
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> dict:
    lines = content.splitlines()[:20]
    fm = {}
    in_fm = False
    for line in lines:
        if line.strip() == "---":
            if not in_fm:
                in_fm = True
                continue
            else:
                break
        if in_fm and ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def scan_topics(topics_dir: Path) -> list:
    if not topics_dir.exists():
        return []
    results = []
    for f in topics_dir.glob("*.md"):
        if f.name == "TOPICS.md":
            continue
        try:
            with open(f, encoding="utf-8") as fp:
                head = "".join(fp.readline() for _ in range(20))
            fm = parse_frontmatter(head)
            results.append({
                "path": str(f),
                "topic": fm.get("topic", f.stem),
                "description": fm.get("description", ""),
                "date": fm.get("date", ""),
                "mtime": f.stat().st_mtime,
            })
        except Exception:
            continue
    return results


def score(item: dict, query: str) -> int:
    s = 0
    q = query.lower()
    keywords = re.split(r"[\s,，、]+", q)
    text = f"{item['topic']} {item['description']}".lower()
    for kw in keywords:
        if kw and kw in text:
            s += 1
        if kw and kw in item["topic"].lower():
            s += 2
    return s


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics-dir", required=True)
    parser.add_argument("--query", default="")
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args()

    items = scan_topics(Path(args.topics_dir).expanduser())
    if not items:
        sys.exit(0)

    query = args.query.strip()
    if query:
        scored = [(score(i, query), i) for i in items]
        scored = [(s, i) for s, i in scored if s > 0]
        scored.sort(key=lambda x: (-x[0], -x[1]["mtime"]))
        results = [i for _, i in scored[:args.limit]] or sorted(items, key=lambda x: -x["mtime"])[:args.limit]
    else:
        results = sorted(items, key=lambda x: -x["mtime"])[:args.limit]

    for item in results:
        print(item["path"])


if __name__ == "__main__":
    main()
```

### Step 7 — 更新 settings.json

读取 `~/.claude/settings.json`，在 `hooks` 字段中合并写入以下配置（保留所有现有字段，若已有相同 command 则跳过）：

```json
{
  "hooks": {
    "PreCompact": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "bash ~/.claude/hooks/pre-compact-inject.sh"}]
      }
    ],
    "PostCompact": [
      {
        "matcher": "",
        "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/post-compact-save-topic.py"}]
      }
    ]
  }
}
```

### Step 8 — 确认安装完成

展示安装结果：

```
✅ Topic Memory 安装完成！

已创建：
  ~/.claude/hooks/pre-compact-inject.sh
  ~/.claude/hooks/post-compact-save-topic.py
  ~/.claude/skills/recall/SKILL.md
  ~/.claude/skills/recall/scripts/search_topics.py

~/.claude/settings.json 已更新（PreCompact + PostCompact hooks）

使用方式：
  自动：每次 compact 时自动提取并保存任务 topic
  召回：/recall <关键词>  搜索并注入历史 topic

重启 Claude Code 后生效。
```

## 注意事项

- settings.json 合并时保留所有现有字段（env、permissions 等）
- 若 hooks 数组中已有相同 command，不重复添加
- 写文件时使用 Write 工具，不要用 echo/heredoc bash 命令（避免特殊字符转义问题）
