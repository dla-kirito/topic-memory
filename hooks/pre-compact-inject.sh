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
