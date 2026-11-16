---
title: "Provenance-tracking policy decides where agent output may go based on what the agent read"
date: 2026-11-16
theme: agent-authorization
evidence: [9444ee7529255986]
---
TrustGraph, an open-source Show HN project, targets the gap read permissions leave open: an agent allowed to read private repos and allowed to open public PRs can chain the two, as Invariant Labs showed in 2025.

It records what each output was **derived from** across every step and handoff, then checks a policy file that says who may read data derived from each source and where each action sends output. Answers are **allow, needs approval, or deny** with a reason. Approval never widens readership, anything unnamed is denied, and each policy ships with its own test cases (project-described).

For builders: this is taint tracking for agents. Gate writes on data lineage, not only on tool permissions.
