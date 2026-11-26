---
title: "A 27-day agent-team log: state on disk survived 35 sessions; a broken wait tool burned 77% of a day's tokens"
date: 2026-11-26
theme: production-evidence
evidence: [2f8b0a8cbf6c6378]
also: [agent-cost]
---
A solo builder ran a coordinator session that splits requests into briefs for worker sessions and sub-agents. The context window filled by mid-afternoon, so a hook warns at 70% and 85% and the coordinator writes a handoff file before restarting: **35 coordinator sessions in 27 days**. The rule that held: state lives on disk, never in the conversation.

What broke was the plumbing. One worker's "wait for posts" tool returned immediately, so it looped at about **290,000 tokens a turn** and used about **77% of ~1.3B** context tokens read that day. Another worker reported waiting 30 minutes after one. A 30-minute listener timeout caused 24 empty wake-ups in a day.

For builders: put a token budget on idle loops, and never trust an agent's report of elapsed time.
