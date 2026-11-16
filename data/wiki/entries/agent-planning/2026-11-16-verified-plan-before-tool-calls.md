---
title: "Formally verifying the plan before any tool call raised task success 1.7x with zero policy violations"
date: 2026-11-16
theme: verify-and-replan
evidence: [4dca535a21e12015]
also: [agent-reliability]
---
Soteria targets a common failure of runtime guardrails: blocking an unsafe action stops the violation but strands the agent with no way to recover.

The agent first writes a **structured hierarchical plan**, which is formally verified against domain specifications before any tool runs. During execution the verified plan does two jobs: it keeps the trajectory spec-conformant, and it tells the agent what to do next when an action is blocked. Across several tool-use benchmarks it reached **1.7x the average task success** of the best baselines with **no policy violations** (paper-reported).

For builders: a block needs a recovery path. Checking a plan against policy up front gives the agent one, instead of trading safety for completion.
