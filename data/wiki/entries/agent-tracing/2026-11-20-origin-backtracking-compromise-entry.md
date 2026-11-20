---
title: "Origin maps agent trajectory logs to code-level calls to find where an attack entered"
date: 2026-11-20
theme: diagnosis
evidence: [a7be3c1e57e039be]
also: [prompt-injection]
---
After an agent security incident, analysts must find the compromise entry point. Trajectory logs record what the agent did at the functionality level, but candidate entry points are function calls in the application code, so the analyst traces between layers by hand. Origin builds a **cross-layer dependency graph** linking inferred functionality regions to variables in a taint-propagation subgraph, and gives analysts a query language over it.

In case studies on five popular agent applications and eight attacks, an analyst using Origin found every entry point. For builders: post-incident forensics needs traces joined to code-level data flow, not only the agent's own step log.
