---
title: "LangSmith's Perceived Error signal finds agent mistakes from what users flagged"
date: 2026-08-19
theme: verifying-the-work
evidence: [c4b4a85beb63030f]
---
LangSmith **Tuned Evaluators** attach quality feedback to production traces, starting with a **Perceived Error** signal that surfaces agent mistakes from user reactions in production.

It adds a user-facing check alongside independent judges and trace mining: the agent's "done" is tested against whether the user thought it was right. The eval-tooling side of the release is on [agent evaluation](/topic/agent-evaluation).
