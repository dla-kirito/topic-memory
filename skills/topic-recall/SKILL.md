---
name: topic-recall
description: 召回历史 topic 上下文注入当前 session。当用户说"召回"、"/recall"、"找一下之前"、"上次做过"、"之前的任务"、"记得之前"时触发。
---

# Topic Memory Recall

从当前项目的 topic 历史中找到相关上下文，注入当前 session。

## 定位脚本

```bash
SCRIPT_DIR="$(find ~/.claude ~/Library/Caches/coco/plugins -path '*/topic-recall/scripts/search_topics.py' -print -quit 2>/dev/null | xargs dirname 2>/dev/null)"
```

## 工作流

### Step 1 — 确定 topics 目录

当前项目的 topics 目录路径规则：
```
~/.claude/projects/<sanitized-cwd>/topics/
```

其中 `<sanitized-cwd>` 是当前工作目录路径，将 `/` 替换为 `-`（首字符去掉）。

用 bash 计算：
```bash
CWD=$(pwd)
SANITIZED=$(echo "$CWD" | sed 's|/|-|g')
TOPICS_DIR="$HOME/.claude/projects/${SANITIZED}/topics"
```

若 topics 目录不存在，告知用户"当前项目还没有保存的 topic，完成一次 compact 后会自动生成"，结束。

### Step 2 — 搜索相关 topic

```bash
python3 "$SCRIPT_DIR/search_topics.py" \
  --topics-dir "$TOPICS_DIR" \
  --query "<用户的关键词或任务描述>"
```

输出：每行一个匹配的 topic 文件绝对路径（按相关度排序，最多 5 个）。

若无关键词（用户只说"召回"）：
```bash
python3 "$SCRIPT_DIR/search_topics.py" \
  --topics-dir "$TOPICS_DIR"
```
返回最近修改的 5 个 topic。

### Step 3 — 展示候选列表

读取每个返回的 topic 文件，只展示 frontmatter 的 `description` 和 `date`，让用户确认：

```
找到以下相关 topic，请选择要召回的：

1. react-performance-optimization（2026-04-14）
   首页 LCP 优化，放弃 SSR 改用预加载，目标 4.2s → 2s

2. auth-refactor（2026-04-10）
   认证模块重构，从 JWT 改为 session cookie
```

询问用户选择（支持序号或"全部"）。

### Step 4 — 注入选定 topic

读取用户选定的 topic 文件完整内容，直接在对话中展示并说明：

"已召回 topic [xxx]，以下是上次任务的关键上下文，我会据此继续工作："

然后展示 topic 内容（任务目标、关键决策、用户偏好、踩坑记录、当前状态）。

## 注意事项

- 若找不到任何 topic，提示用户"还没有相关历史，完成一次 compact 后会自动保存"
- 召回内容只展示，不自动覆盖用户当前任务，由用户决定是否采纳
