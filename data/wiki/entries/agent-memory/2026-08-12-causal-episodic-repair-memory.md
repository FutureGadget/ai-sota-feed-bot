---
title: "MERIT keeps verified repairs as memory so later episodes don't rediscover the fix"
date: 2026-08-12
theme: recall-and-curation
evidence: [7339a1b37836ee76]
---
Agents that repair a failure usually discard the successful correction, so a later episode with the same bug starts from scratch. **MERIT**, a training-free Text-to-SQL agent, keeps a dual-polarity memory of oracle-verified corrections and of directions that failed. A deterministic classifier assigns a coarse failure type that conditions retrieval, and only finalized earlier episodes are eligible.

"What worked last time, and why" becomes its own memory object, distinct from facts or preferences.
