#!/bin/bash
# PreCompact hook: 向 compact 提示词注入结构化提取指令
# 同时注入已有 topic 列表，帮助 Claude 跨 session 复用 slug，实现 topic 连续性
# Claude 在生成压缩摘要时会附带输出 topic-json 块
# PostCompact hook 随后解析该块并写入 topic 文件

# 读取 stdin，提取 transcript_path（PreCompact hook 通过 stdin 传入）
INPUT=$(cat)
TRANSCRIPT_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('transcript_path', ''))
except Exception:
    print('')
" 2>/dev/null)

# 推导 topics 目录（transcript_path 的父目录 + /topics/TOPICS.md）
TOPICS_INDEX=""
if [ -n "$TRANSCRIPT_PATH" ]; then
    PROJECT_DIR=$(dirname "$TRANSCRIPT_PATH")
    TOPICS_INDEX="$PROJECT_DIR/topics/TOPICS.md"
fi

# 输出结构化提取指令
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
  "files_and_functions": ["path/to/file.ts — 作用简述", "src/utils/foo.py — 用途说明"],
  "workflow": ["命令1及用途，如 npm run dev — 启动开发服务器", "命令2及用途"],
  "current_status": "当前进度和下一步"
}
```

字段说明：
- "files_and_functions"：本次任务涉及的关键文件和函数，格式"路径 — 一句话说明"。若无明显关键文件可留空 []。
- "workflow"：常用的构建/测试/运行命令及顺序，格式"命令 — 用途"。若无明显 workflow 可留空 []。

注意：如果对话内容不涉及具体任务（如纯聊天），可以省略此块。
INSTRUCTIONS

# 若当前项目已有 topic，提示 Claude 复用 slug（跨 session 连续性的关键）
if [ -n "$TOPICS_INDEX" ] && [ -f "$TOPICS_INDEX" ]; then
    echo ""
    echo "【重要】当前项目已有以下 topics。如本次对话是其中某个 topic 的延续，请使用相同的 slug，不要新建："
    cat "$TOPICS_INDEX"
fi

exit 0
