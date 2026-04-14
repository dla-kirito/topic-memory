#!/usr/bin/env python3
"""
PostCompact hook: 从 compactSummary 解析 topic-json 块，写入 topic 文件和索引。

输入（stdin）：
{
  "hook_event_name": "PostCompact",
  "session_id": "...",
  "transcript_path": "~/.claude/projects/<slug>/<session-id>.jsonl",
  "cwd": "...",
  "trigger": "auto" | "manual",
  "compactSummary": "<Claude 生成的完整摘要文本>"
}

行为：
- 解析 compactSummary 中的 ```topic-json ... ``` 块
- 写入 ~/.claude/projects/<slug>/topics/<topic-slug>.md
- 更新 TOPICS.md 索引
- 任何异常都静默处理，不阻断 compact 后续流程
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path


def get_topics_dir(transcript_path: str) -> Path:
    """从 transcript_path 推导 topics 目录路径"""
    # transcript_path: ~/.claude/projects/<slug>/<session-id>.jsonl
    # topics_dir:      ~/.claude/projects/<slug>/topics/
    project_dir = Path(transcript_path).expanduser().parent
    return project_dir / "topics"


def parse_topic_json(summary: str) -> dict | None:
    """从 compactSummary 中提取并解析 ```topic-json ... ``` 块"""
    pattern = r"```topic-json\s*\n(.*?)\n```"
    match = re.search(pattern, summary, re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1).strip())
    except json.JSONDecodeError:
        return None


def slugify(s: str) -> str:
    """确保 slug 安全（只保留字母数字和横线）"""
    s = re.sub(r"[^\w-]", "-", s.lower())
    s = re.sub(r"-+", "-", s).strip("-")
    return s or "untitled"


def read_frontmatter(content: str) -> dict:
    """简单解析 YAML frontmatter（只处理字符串和列表字段）"""
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
        # 简单列表解析 [a, b, c]
        if val.startswith("[") and val.endswith("]"):
            items = [x.strip().strip('"').strip("'") for x in val[1:-1].split(",")]
            fm[key] = [i for i in items if i]
        else:
            fm[key] = val.strip('"').strip("'")
    return fm


def write_topic_file(topics_dir: Path, data: dict, session_id: str):
    """写入或更新单个 topic 文件"""
    slug = slugify(data.get("topic_slug", "untitled"))
    topic_file = topics_dir / f"{slug}.md"
    today = datetime.now().strftime("%Y-%m-%d")

    if topic_file.exists():
        # 合并更新已有文件
        existing = topic_file.read_text(encoding="utf-8")
        fm = read_frontmatter(existing)

        # 更新 sessions 列表（去重追加）
        sessions = fm.get("sessions", [])
        if isinstance(sessions, str):
            sessions = [sessions]
        if session_id and session_id not in sessions:
            sessions.append(session_id)

        # 追加新的 decisions 和 pitfalls（去重）
        body_start = existing.find("\n---", 3)
        body_start = existing.find("\n", body_start + 1) + 1 if body_start != -1 else 0
        existing_body = existing[body_start:] if body_start else existing

        new_decisions = data.get("decisions", [])
        new_pitfalls = data.get("pitfalls", [])

        # 提取已有 pitfalls（去重追加，保留历史踩坑记录）
        existing_pitfalls_match = re.search(
            r"## 踩坑记录\n(.*?)(?=\n##|\Z)", existing_body, re.DOTALL
        )
        existing_pitfalls_text = existing_pitfalls_match.group(1) if existing_pitfalls_match else ""

        # decisions：覆盖（compact 已看完整历史，最新结果最准确，追加会引入矛盾条目）
        # pitfalls：追加去重（踩坑记录是历史教训，即使已解决也有参考价值）
        appended_pitfalls = [p for p in new_pitfalls if p not in existing_pitfalls_text]

        # 重建文件
        new_content = _build_topic_content(
            slug=slug,
            description=data.get("description", fm.get("description", "")),
            sessions=sessions,
            date=today,
            task_goal=data.get("task_goal", ""),
            decisions=new_decisions,
            preferences=data.get("preferences", []),
            pitfalls=_parse_existing_list(existing_pitfalls_text) + appended_pitfalls,
            current_status=data.get("current_status", ""),
        )
    else:
        # 新建文件
        sessions = [session_id] if session_id else []
        new_content = _build_topic_content(
            slug=slug,
            description=data.get("description", ""),
            sessions=sessions,
            date=today,
            task_goal=data.get("task_goal", ""),
            decisions=data.get("decisions", []),
            preferences=data.get("preferences", []),
            pitfalls=data.get("pitfalls", []),
            current_status=data.get("current_status", ""),
        )

    topic_file.write_text(new_content, encoding="utf-8")
    return slug, data.get("description", "")


def _parse_existing_list(text: str) -> list:
    """从 markdown 列表文本提取条目"""
    items = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- "):
            items.append(line[2:].strip())
    return items


def _build_topic_content(
    slug, description, sessions, date, task_goal, decisions, preferences, pitfalls, current_status
) -> str:
    sessions_str = "[" + ", ".join(sessions) + "]"
    lines = [
        "---",
        f"topic: {slug}",
        f"description: {description}",
        f"sessions: {sessions_str}",
        f"date: {date}",
        "---",
        "",
    ]
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


def update_topics_index(topics_dir: Path, slug: str, description: str):
    """更新 TOPICS.md 索引（插入或更新对应行，max 200 行）"""
    index_file = topics_dir / "TOPICS.md"
    entry = f"- [{slug}]({slug}.md) — {description}"

    if index_file.exists():
        lines = index_file.read_text(encoding="utf-8").splitlines()
    else:
        lines = []

    # 查找并替换已有同 slug 的行，否则插入到开头（最新在前）
    slug_pattern = f"- [{slug}]"
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(slug_pattern):
            new_lines.append(entry)
            updated = True
        else:
            new_lines.append(line)

    if not updated:
        new_lines.insert(0, entry)

    # 限制 200 行
    new_lines = new_lines[:200]
    index_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main():
    try:
        raw = sys.stdin.read().strip()
        if not raw:
            sys.exit(0)

        hook_input = json.loads(raw)
        compact_summary = hook_input.get("compactSummary", "")
        transcript_path = hook_input.get("transcript_path", "")
        session_id = hook_input.get("session_id", "")

        if not compact_summary or not transcript_path:
            sys.exit(0)

        # 解析 topic-json 块
        data = parse_topic_json(compact_summary)
        if not data:
            print("[Topic Memory] 本次 compact 未提取到 task context（纯对话或 Claude 遗漏），可用 /topic-note 手动保存")
            sys.exit(0)

        # 确保 topics 目录存在
        topics_dir = get_topics_dir(transcript_path)
        topics_dir.mkdir(parents=True, exist_ok=True)

        # 写 topic 文件
        slug, description = write_topic_file(topics_dir, data, session_id)

        # 更新索引
        update_topics_index(topics_dir, slug, description)

        # 可选：输出到 stdout（会显示给用户）
        print(f"[Topic Memory] 已保存 topic: {slug}")

    except Exception:
        # 静默处理，不阻断 compact 后续流程
        sys.exit(0)


if __name__ == "__main__":
    main()
