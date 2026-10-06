---
title: "SWE-Gate: 221 of 644 test-passing repairs fail real review constraints"
date: 2026-09-05
theme: coding-benchmarks
evidence: [cc74131efa65cff2]
---
**SWE-Gate** (303 instances) adds review-derived acceptance constraints from real PR feedback to repository-level coding evaluation. Across four model backends, **221 of 644 functionally passing repairs** violate those constraints.

Functional-test-only benchmarks overestimate what an agent can actually merge. If your gate is human review, your eval needs review-style checks too.
