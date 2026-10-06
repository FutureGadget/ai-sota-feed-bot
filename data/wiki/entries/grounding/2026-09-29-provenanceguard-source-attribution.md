---
title: "ProvenanceGuard checks per claim that an MCP agent cites the source a fact actually came from"
date: 2026-09-29
theme: proving-attribution
evidence: [afa8c33f8eb7996a]
---
Multi-tool agents can state a true fact but attribute it to the wrong source, for example citing the account record for a fact that lives in the policy document. Pooled faithfulness scores miss this **cross-source conflation**.

ProvenanceGuard is a post-generation verifier that reads the captured tool trace with source IDs and never pools evidence. It splits the answer into claims, routes each to its likeliest source, checks support, compares that source with the one cited, and emits **per-claim verdicts plus an allow/block decision**, with no agent retraining.
