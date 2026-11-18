---
title: "Delegation retrieves more conflicting evidence but detects fewer conflicts, because handoffs drop one side"
date: 2026-11-18
theme: shared-context
evidence: [841194ca9dd70bcb]
also: [agent-memory]
---
A benchmark built on Harvey LAB document-review tasks planted factual conflicts and traced how evidence moved between workers and the lead. Pooled across three models at comparable generation spend, requiring delegation raised retrieval of both conflicting claims from **50.2% to 68.7%**. Conflict detection still fell, from **16.2% to 13.2%**.

The loss is in the handoff. Workers reported both claims for only **35.2%** of retrieved pairs. When one worker read both claims, detection beat a single agent. When the claims were split across workers, it fell below. For builders: send claims to the lead with their sources, not as summaries, or route documents that could contradict each other to the same worker.
