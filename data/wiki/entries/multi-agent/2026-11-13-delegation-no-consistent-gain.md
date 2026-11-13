---
title: "Delegating search to a sub-agent gives no consistent accuracy gain and hurts on facts the orchestrator lacks"
date: 2026-11-13
theme: when-it-pays
evidence: [19aefaffb32649b7]
also: [agent-orchestration]
---
A study of delegation modes in generative search used datasets split into pre- and post-training-cutoff questions. Delegation showed no consistent accuracy improvement over non-delegated setups, with the effect varying by model and task.

On post-cutoff questions, where the orchestrator cannot resolve the answer from its own knowledge, delegation substantially degraded accuracy. Direct tool use by the same model did much better.

Three recurring failure modes:

- the orchestrator distorts the query it hands off;
- the sub-agent uses tools inefficiently;
- information is lost or ignored between agents.

For builders: give the main loop the search tool before adding a search sub-agent, and test handoffs on questions the orchestrator cannot answer alone. Paper-reported; the abstract gives no headline number.
