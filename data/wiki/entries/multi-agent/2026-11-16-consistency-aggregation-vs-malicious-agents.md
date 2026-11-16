---
title: "Consensus-based aggregation blocks optimized malicious sub-agent responses that defeat standard rules"
date: 2026-11-16
theme: oversight-and-safety
evidence: [d761218419b3b591]
also: [prompt-injection]
---
A paper treats the orchestrator's **aggregation rule** as the attack surface. Its ReMA attack iteratively refines a malicious sub-agent's answer against a surrogate system until it steers the final result, in targeted and untargeted variants.

Existing aggregation rules proved vulnerable. The proposed defense, **SecMAS**, picks the response most semantically consistent with a sufficiently large subset of the other agents, and comes with theoretical guarantees. It held against all evaluated attacks, including adaptive ones, with utility comparable to standard rules (paper-reported).

For builders: if one compromised or injected sub-agent can decide the output, the merge step is a single point of failure. Require agreement across independent agents before an answer wins.
