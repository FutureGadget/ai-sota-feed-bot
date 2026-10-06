---
title: "LangSmith Trajectories renders an agent session as one chat-style thread"
date: 2026-09-24
theme: diagnosis
evidence: [b60131f089d99489]
---
LangSmith's **Trajectories** view shows a full agent session (user turns, tool calls, sub-agent handoffs) as one conversational thread instead of a tree of nested spans.

It trades the completeness of the span tree for a fast top-to-bottom read. It targets long-running sessions, where expanding every span by hand is the bottleneck.
