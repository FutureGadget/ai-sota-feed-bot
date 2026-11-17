---
title: "Delegating to a cheaper sub-agent drops system safety to the sub-agent's level"
date: 2026-11-17
theme: oversight-and-safety
evidence: [e92a16b627ebc27c]
also: [prompt-injection]
---
Researchers planted a forged record in a file store and asked Claude Code, Codex, and a reference harness, all unmodified, to answer questions from it. Strong orchestrators searching the store themselves made almost **zero** harmful revisions in over 1,000 trials.

When the same orchestrator delegated reading to a cheaper sub-agent, as these harnesses are built to do, failures rose to **20/180, 44/180, 75/180 and 553/900**. In simulations over 18 models, five aggregators that were almost never unsafe alone repeated a corrupted sub-agent's error in **751/757** trials.

For builders: an orchestrator does not filter what its sub-agents read. Treat the weakest model in the delegation chain as the system's safety level, and give it the same input controls as the orchestrator.
