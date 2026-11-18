---
title: "A shadow-mode multi-agent system found 92 documentation gaps from 499 support tickets in 43 days"
date: 2026-11-18
theme: production-evidence
evidence: [6c4aeadbb63ee69f]
---
**TriAgent** is a deployed multi-agent system that reads resolved support tickets and code-documentation mismatches, then proposes documentation fixes. In 43 days of shadow mode it triaged **499 tickets** and surfaced **92 gaps**. A three-family LLM judge panel scored **81.1%** of its checkable claims correct (245 of 302). On length-matched pairs, the panel preferred its replies over the human engineer's 70.5% to 23.2%.

The useful finding is that agent and human answers were complementary. Humans often surfaced facts the docs buried or lacked, and each of those became a reviewed fix. After a repair, blinded judges preferred the agent's new answer to the same ticket. Every number here is judge-scored, not user-measured.
