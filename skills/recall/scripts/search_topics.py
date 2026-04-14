#!/usr/bin/env python3
"""
search_topics.py — 搜索 topics 目录中的相关 topic 文件

用法：
  python3 search_topics.py --topics-dir <path> [--query <关键词>]

输出：
  每行一个匹配的 topic 文件绝对路径（按相关度/修改时间排序，最多 5 个）
"""

import argparse
import os
import re
import sys
from pathlib import Path


def parse_frontmatter(content: str) -> dict:
    """读取文件前 20 行中的 YAML frontmatter"""
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


def scan_topics(topics_dir: Path) -> list[dict]:
    """扫描 topics 目录，读取所有 topic 文件的 frontmatter"""
    if not topics_dir.exists():
        return []

    results = []
    for f in topics_dir.glob("*.md"):
        if f.name == "TOPICS.md":
            continue
        try:
            # 只读前 20 行，高效
            with open(f, encoding="utf-8") as fp:
                head = "".join(fp.readline() for _ in range(20))
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


def keyword_match_score(item: dict, query: str) -> int:
    """简单关键词匹配打分（不需要 API）"""
    score = 0
    query_lower = query.lower()
    keywords = re.split(r"[\s,，、]+", query_lower)

    text = f"{item['topic']} {item['description']}".lower()
    for kw in keywords:
        if kw and kw in text:
            score += 1
        # topic slug 精确匹配加分
        if kw and kw in item["topic"].lower():
            score += 2

    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--topics-dir", required=True, help="topics 目录路径")
    parser.add_argument("--query", default="", help="搜索关键词")
    parser.add_argument("--limit", type=int, default=5, help="最多返回数量")
    args = parser.parse_args()

    topics_dir = Path(args.topics_dir).expanduser()
    items = scan_topics(topics_dir)

    if not items:
        sys.exit(0)

    query = args.query.strip()

    if query:
        # 关键词匹配，过滤掉得分为 0 的
        scored = [(keyword_match_score(item, query), item) for item in items]
        scored = [(s, i) for s, i in scored if s > 0]
        # 分数相同时按修改时间降序
        scored.sort(key=lambda x: (-x[0], -x[1]["mtime"]))
        results = [i for _, i in scored[:args.limit]]

        # 若关键词匹配无结果，退回到时间排序
        if not results:
            results = sorted(items, key=lambda x: -x["mtime"])[:args.limit]
    else:
        # 无 query：最近修改的
        results = sorted(items, key=lambda x: -x["mtime"])[:args.limit]

    for item in results:
        print(item["path"])


if __name__ == "__main__":
    main()
