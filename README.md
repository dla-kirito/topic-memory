# Topic Memory for Claude Code

> **Never lose your session context to compact again.**

Claude Code's `/compact` command compresses conversation history — great for managing context limits, but it destroys the task context you've carefully built up: decisions made, preferences tuned, pitfalls discovered. Topic Memory saves all of that automatically.

## How it works

```
① PreCompact hook fires
   └── Injects extraction instructions into the compact prompt

② Compact runs (Claude summarizes + extracts topic-json)
   └── One model call — zero extra API cost

③ PostCompact hook fires
   └── Parses the topic-json block from the summary
   └── Writes ~/.claude/projects/<project>/topics/<slug>.md
   └── Updates TOPICS.md index

④ On demand: /recall <keyword>
   └── Scans topic index → shows matches → injects into session
```

## Installation

```bash
curl -sSL https://raw.githubusercontent.com/dla-kirito/topic-memory/main/install.sh | bash
```

Then restart Claude Code.

## Usage

**Automatic** — every compact saves a topic file. No action needed.

**Recall** — when starting a new session or after compact:

```
/recall performance optimization
/recall auth refactor
/recall                          # shows 5 most recent topics
```

Claude will find matching topics, show a summary, and inject the selected context into your session.

## What gets saved

Each topic file captures:

```markdown
---
topic: react-performance-optimization
description: LCP optimization, replaced SSR with preloading, target 4.2s → 2s
sessions: [abc123, def456]
date: 2026-04-14
---

## Task Goal
Optimize homepage LCP from 4.2s to 2s

## Key Decisions
- Replaced SSR with preloading (reason: hydration cost too high)
- Using sharp instead of next/image (reason: customization needs)

## User Preferences
- Avoid over-abstraction, keep code straightforward
- Only test critical paths

## Pitfalls
- next/image blur placeholder conflicts with sharp

## Current Status
Image optimization done, working on JS bundle splitting
```

## Topic storage location

```
~/.claude/projects/<your-project>/topics/
├── TOPICS.md                    # index (max 200 entries)
├── react-performance.md
└── auth-refactor.md
```

Topics are per-project and persist across sessions.

## Difference from Claude Code's built-in Memory

| | Built-in Memory | Topic Memory |
|---|---|---|
| What it stores | Who you are (preferences, role) | What you're doing (task context) |
| Written by | Claude, when it decides to | Automatically on every compact |
| Loaded | Every session, automatically | On demand via `/recall` |
| Fades | Slowly | Quickly (task state changes) |

They complement each other — Memory is your profile, Topic Memory is your task notebook.

## Files

```
topic-memory/
├── install.sh                        # one-command installer
├── hooks/
│   ├── pre-compact-inject.sh         # PreCompact hook
│   └── post-compact-save-topic.py    # PostCompact hook
└── skills/
    ├── recall/
    │   ├── SKILL.md                  # /recall skill
    │   └── scripts/search_topics.py
    └── install-topic-memory/
        └── SKILL.md                  # /install-topic-memory skill
```

## Requirements

- Claude Code 2.x
- Python 3.x (pre-installed on macOS/Linux)

## License

MIT
