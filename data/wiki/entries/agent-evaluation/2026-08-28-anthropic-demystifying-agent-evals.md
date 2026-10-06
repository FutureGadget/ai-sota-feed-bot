---
title: "Anthropic: three grader types, pass@k vs pass^k, and 20-50 tasks from real failures"
date: 2026-08-28
theme: eval-in-production
evidence: [6c790a16de0afd2b]
---
Anthropic's "Demystifying evals for AI agents" frames every agent eval as input delivery, agent processing, and grading, with three grader types that trade cost, flexibility, and determinism: **code-based, model-based, human**.

For non-determinism it reports two metrics over repeated runs: **pass@k** (at least one of k attempts succeeds) and **pass^k** (all k succeed). The suggested start is **20-50 tasks** mined from actual production failures. Use pass^k when users need it to work every time.
