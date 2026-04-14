---
name: topic-note
description: 手动将当前 session 关键上下文保存为 topic 文件（立即保存，无需等 compact）。当用户说"/note"、"/note <topic名称>"、"保存进度"、"记录一下"、"记一下"时触发。
---

# Note — 手动保存 Topic

将当前 session 的关键上下文立即保存（或更新）到 topic 文件。无需等待 compact，随时可用。

## 定位搜索脚本

SCRIPT_DIR="$(find ~/.claude ~/Library/Caches/coco/plugins -path '*/topic-recall/scripts/search_topics.py' -print -quit 2>/dev/null | xargs dirname 2>/dev/null)"

## 工作流

### Step 1 — 确定 topics 目录

CWD=$(pwd)
SANITIZED=$(echo "$CWD" | sed 's|/|-|g')
TOPICS_DIR="$HOME/.claude/projects/${SANITIZED}/topics"

若 topics 目录不存在，创建它：mkdir -p "$TOPICS_DIR"

### Step 2 — 确认目标 topic

获取最近 20 个 topic 的 manifest：
```bash
python3 "$SCRIPT_DIR/search_topics.py" --topics-dir "$TOPICS_DIR" --format manifest --limit 20
```

**如果用户提供了 topic 名称**（如 `/note react-performance`）：
- 从 manifest 中语义判断最匹配的已有 topic
- 若找到匹配项，展示其 slug + description，询问用户确认是否更新该 topic
- 若确实无匹配，以该名称作为 slug 新建

**如果用户未提供名称**（直接 `/note`）：
- 展示 manifest 中最近 5 个 topic 的 slug + description
- 询问用户："要更新以上某个 topic，还是新建一个？"

### Step 3 — 提炼当前 session 上下文

根据当前对话内容，生成以下字段：
- **topic_slug**：英文短横线标识符（更新已有 topic 时沿用原 slug，新建时自行生成）
- **description**：一句话描述任务（50字以内）
- **task_goal**：核心目标是什么
- **decisions**：关键决策列表，每条含原因（如"用 X 而非 Y，原因：Z"）
- **preferences**：观察到的用户编码/工作偏好
- **pitfalls**：踩坑记录或失败的尝试
- **files_and_functions**：关键文件路径及用途，格式"path/to/file — 一句话说明"
- **workflow**：常用构建/测试/运行命令及顺序，格式"命令 — 用途"
- **current_status**：当前进度和下一步计划

### Step 4 — 写入 topic 文件

**新建** `$TOPICS_DIR/<slug>.md`，写入以下格式：

```
---
topic: <slug>
description: <description>
sessions: []
date: <今天日期 YYYY-MM-DD>
---

## 任务目标
<task_goal>

## 关键决策
- <decision1>
- <decision2>

## 用户偏好
- <pref1>

## 踩坑记录
- <pitfall1>

## 关键文件
- <path/to/file — 用途说明>

## 工作流程
- <命令 — 用途>

## 当前状态
<current_status>
```

**更新已有文件**：先用 Read 工具读取现有内容，然后合并后用 Write 工具覆盖写入：
- `sessions` 字段：在列表末尾追加当前 session_id（如已知）；去重
- `decisions`：覆盖为最新提炼的内容（compact 看完整历史，最新最准确）
- `pitfalls`：去重追加（历史教训不消失）
- `files_and_functions`：覆盖为最新（最新最准）
- `workflow`：覆盖为最新（最新最准）
- `current_status`、`task_goal`、`description`：覆盖为最新
- `date`：更新为今天

### Step 5 — 更新 TOPICS.md 索引

读取（或创建）`$TOPICS_DIR/TOPICS.md`，更新对应行：
- 格式：`- [slug](slug.md) — description`
- 已有相同 slug 的行则替换，否则插入到文件开头（最新在前）
- 保持 max 200 行

### Step 6 — 确认

告知用户："已保存 topic [<slug>] ✓"，并简要列出保存的关键决策和当前状态。
