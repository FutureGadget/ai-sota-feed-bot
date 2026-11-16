---
title: "Agent verifiers flip up to ~31% of verdicts when the trajectory is compacted or delegated"
date: 2026-11-16
theme: trusting-the-judge
evidence: [a44ee00fea440f11]
also: [agent-evaluation, context-compaction]
---
A paper tests whether an LLM verifier's verdict survives when the **same frozen execution** is shown through composed tools, a delegation boundary, or a compacted history. Task, trajectory, outcome, and criterion stay fixed; only what the verifier can see changes.

Across four benchmarks, seven verifier models, and four protocols, **transport failure reached about 31%** under macro abstraction plus delegation. Direct verification tended to give wrong verdicts; evidence-grounded protocols tended to abstain instead. Restoring execution provenance recovered **85.5%** of the failures (paper-reported).

For builders: a judge's accuracy on full traces says little about its accuracy on summarized or sub-agent traces. Pass provenance through to the grader, and validate the judge on the view it will actually see.
