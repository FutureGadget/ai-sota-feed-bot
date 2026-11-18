---
title: "Judge guardrail prompts can be selected with a statistical bound on the missed-attack rate"
date: 2026-11-18
theme: trusting-the-judge
evidence: [4cd0a215f3b11ad1]
also: [prompt-injection]
---
Judge guardrails are usually tuned by editing the system prompt for average accuracy. This paper instead treats prompt choice as a constrained problem: maximize the benign pass rate while keeping the missed-attack rate below a chosen level α, certified with distribution-free confidence bounds on a held-out set. **CPS** certifies a fixed pool of generated prompts. **CRISP** steers generation toward prompts that can be certified, using rewrites guided by hard examples.

Across prompt injection, system-prompt leakage and sensitive-data disclosure, the certified prompts kept missed attacks at the target level on held-out tests. Utility rose as α was relaxed. For builders, this turns "the guardrail prompt seems fine" into a stated, checkable risk budget. The bound only holds while live traffic matches the held-out set.
