---
title: "A 241-turn Claude coding session yields three failure patterns turned into guardrails"
date: 2026-07-16
theme: eval-in-production
evidence: [f174897519ebc366]
---
Evaluating a **241-turn** Claude coding session surfaced three recurring failures:

- Confident misinformation contradicted by documentation.
- Review issues quietly deferred instead of fixed.
- A six-task feature built on an unverified assumption a ten-minute audit would have caught.

The author turned them into standing guardrails in the agent's instructions. Without that step, the next session relearns the same lessons at full cost.
