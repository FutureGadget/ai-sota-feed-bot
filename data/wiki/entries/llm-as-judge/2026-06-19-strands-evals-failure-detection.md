---
title: "AWS Strands Evals returns categorized failures with causal chains"
date: 2026-06-19
theme: structured-verdicts
evidence: [12500c0bbe5e4d6f]
---
AWS's Strands Evals detectors read a full agent trace and return **categorized failures** with confidence scores, causal chains that link a root cause to its downstream symptoms, and a fix recommendation.

The shift is from one scalar score to a verdict an engineer can act on: which step failed, why, and what to change.
