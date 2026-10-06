---
title: "ActionRail checks an agent's proposed action against ground-truth business data before it executes"
date: 2026-07-27
theme: proving-attribution
evidence: [5ca9aca0e46db978]
---
ActionRail, an open-source framework from ToolJet, adds **runtime value and action grounding**: before an agent's proposed action or value executes, it is checked against ground-truth business data.

Grounding moves from a retrieval-quality score after the fact to a deployable guard in front of side effects, aimed at the value-poisoning failure benchmarks measure (see [agent benchmarks](/topic/agent-benchmarks)).
