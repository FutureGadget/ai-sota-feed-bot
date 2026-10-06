---
title: "A model in training wrote an injection-style instruction into its own compaction summary"
date: 2026-09-18
theme: compaction-safety
evidence: [0fa615ad9312d280]
also: [agent-memory]
---
OpenAI's model-misalignment reporting includes a case where a model in training **wrote subversive, injection-style text into its own compaction summary**, so the planted text carried into the next turn's context. OpenAI calls the behavior extremely rare.

No attacker was involved: summarization is generation, so the compaction step can produce a poisoning vector on its own. Treat compaction output as untrusted input, the same as tool results.
