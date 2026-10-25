---
title: "Deleting an agent's memory record may not remove what its summaries still carry"
date: 2026-10-25
theme: memory-integrity
evidence: [3db8654814ed91dc]
---
AfterDeleteBench audits what persists after deletion in LLM agents that keep external memory and derive extra state, such as summaries, from past interactions. Its premise: deleting the original record need not remove information carried by its descendants.

This is paper-reported from the abstract excerpt; results across systems are not summarized here.

For builders: treat deletion as a graph problem. If summaries, embeddings, or caches are derived from a record, a "forget this" request or retention policy has to propagate to every derived artifact. Track provenance from derived memory back to source records, and test deletion by probing the agent afterward.
