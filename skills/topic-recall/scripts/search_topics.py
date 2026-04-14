#!/usr/bin/env python3
"""
search_topics.py — 列出 topics 目录中的候选文件，供 Claude 做语义相关性判断

用法：
  python3 search_topics.py --topics-dir <path> [--limit N] [--format manifest|paths]

输出：
  manifest（默认）：每行 "slug (date): description"，供 Claude 语义排序
  paths：每行一个文件绝对路径（兼容旧用法）

设计说明：
  关键词匹配由 Claude 语义判断取代 —— skill 执行时 Claude 已在运行，
  无需额外 API 调用即可完成语义相关性排序（参考 Claude Code 内置 Memory
  的 findRelevantMemories 设计思路）。
  此脚本只负责扫描文件、提取 frontmatter，返回候选池。
"""

import argparse
import re
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> dict:
    """读取文件前 30 行中的 YAML frontmatter"""
    fm = {}
    lines = content.splitlines()[:30]
    if not lines or lines[0].strip() != "---":
        return fm
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm


def scan_topics(topics_dir: Path) -> list[dict]:
    """扫描 topics 目录，读取所有 topic 文件的 frontmatter"""
    if not topics_dir.exists():
        return []

    results = []
    for f in topics_dir.glob("*.md"):
        if f.name == "TOPICS.md":
            continue
        try:
            with open(f, encoding="utf-8") as fp:
                head = "".join(fp.readline() for _ in range(30))
            fm = parse_frontmatter(head)
            results.append({
                "path": str(f),
                "filename": f.name,
                "topic": fm.get("topic", f.stem),
                "description": fm.get("description", ""),
                "date": fm.get("date", ""),
                "mtime": f.stat().st_mtime,
            })
        except Exception:
            continue

    return results


def format_manifest(items: list[dict]) -> str:
    """格式化为 Claude 可读的候选清单，参考 Claude Code memoryScan.formatMemoryManifest"""
    lines = []
    for item in items:
        slug = item["topic"]
        date = item["date"] or "unknown"
        desc = item["description"]
        if desc:
            lines.append(f"- {slug} ({date}): {desc}")
        else:
            lines.append(f"- {slug} ({date})")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics-dir", required=True, help="topics 目录路径")
    parser.add_argument("--limit", type=int, default=20, help="最多返回候选数量（默认 20）")
    parser.add_argument("--format", choices=["manifest", "paths"], default="manifest",
                        help="输出格式：manifest（默认，供 Claude 语义排序）或 paths（文件路径）")
    args = parser.parse_args()

    topics_dir = Path(args.topics_dir).expanduser()
    items = scan_topics(topics_dir)

    if not items:
        sys.exit(0)

    # 按修改时间降序（最近的在前），截取候选池
    items = sorted(items, key=lambda x: -x["mtime"])[:args.limit]

    if args.format == "manifest":
        print(format_manifest(items))
    else:
        for item in items:
            print(item["path"])


if __name__ == "__main__":
    main()
