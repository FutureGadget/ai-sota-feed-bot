---
title: "Serving optimizations documented as exact still flip individual graded answers while aggregate accuracy holds"
date: 2026-11-24
theme: serving-runtime-drift
evidence: [3515c9dc9a088b85]
also: [agent-evaluation]
---
*Exact on Paper* tests prefix caching, chunked prefill, and speculative decoding, which serving engines document as output-preserving. Individual graded answers change when these are switched on, even though aggregate benchmark accuracy stays flat. The authors measure the flips against the noise floor of simply reordering the same requests, to separate real effects from batching nondeterminism.

For builders: turning on a serving optimization is a behavior change for any single request. If you replay or regression-test agent runs, pin these engine flags alongside the model version, and compare per-item results, not the average.
