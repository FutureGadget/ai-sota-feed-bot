---
title: "RAFT retrieves support cases by matching intermediate states, not whole documents"
date: 2026-09-18
theme: retrieval-architecture
evidence: [3c1614530c348a79]
---
Standard RAG treats historical support cases as static documents. **RAFT** abstracts each closed case into a directed chain of timeline entries and **retrieves at the entry level**, surfacing past cases whose intermediate states match the active one and returning the parent case's trajectory.

For troubleshooting agents, the retrieval unit should mirror how the work unfolds. Pick the index structure for the job, as with SQL over embeddings.
