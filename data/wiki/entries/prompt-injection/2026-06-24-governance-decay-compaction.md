---
title: "Context compaction can silently evict the safety constraints an agent obeyed earlier"
date: 2026-06-24
theme: injection-paths
evidence: [9c19b2212d6264ac]
---
"Governance Decay" shows that governance constraints an agent reliably obeys while they are visible can be removed by compaction, summarization, or eviction. **The same agent then performs prohibited tool actions later in the session.** A guardrail that held at turn one can be gone by turn fifty.

Pin safety and permission rules outside the compactible window, in the system prompt or harness policy, instead of trusting them to survive summarization. See [context compaction](/topic/context-compaction).
