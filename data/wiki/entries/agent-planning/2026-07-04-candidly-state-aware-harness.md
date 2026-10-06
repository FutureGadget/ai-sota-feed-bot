---
title: "Candidly's per-turn state model halved disengaging turns (23% to 11%)"
date: 2026-07-04
theme: ask-or-proceed
evidence: [a98baa78edc4ea0a]
---
Candidly built an **IO-HMM** over per-turn signals such as message length and semantic alignment. It infers whether a conversation is Engaged, Detailed, Guided, or Disengaging and steers the agent's next turn accordingly.

In production, disengaging turns fell from **23% to 11%** and the Engaged state rose from **53% to 64%**. Inferring mid-episode whether the plan is working, not just scoring the end result, was worth the extra model.
