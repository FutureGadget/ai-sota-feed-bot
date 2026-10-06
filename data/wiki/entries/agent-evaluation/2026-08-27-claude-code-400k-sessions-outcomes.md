---
title: "400,000 Claude Code sessions: verified success rises from 15% for novices to 28-33% for experts"
date: 2026-08-27
theme: eval-in-production
evidence: [a6ebb163a6c3bf17]
---
Anthropic's analysis of roughly **400,000 Claude Code sessions** uses two outcome tiers instead of pass/fail: verified success (a checkable completion signal) and partial success.

- Novices: **15% verified / 77% partial**, abandoning 19% of sessions.
- Intermediate/expert users: 28-33% verified / 91-92% partial, abandoning 5-7%.
- People make ~70% of planning decisions but only 20% of execution decisions; experts trigger about twice the actions per prompt.

"Did it work" and "how much oversight did it take" are separate numbers a production eval should report. See [agent reliability](/topic/agent-reliability).
