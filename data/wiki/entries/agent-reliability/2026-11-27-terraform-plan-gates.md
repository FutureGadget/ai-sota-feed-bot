---
title: "AI-written Terraform stays safe when deterministic plan checks, not a second AI, gate every apply"
date: 2026-11-27
theme: deterministic-boundaries
evidence: [7d749495f7e10f67]
also: [agent-sandboxing]
---
A field write-up on AI-written infrastructure code argues that valid Terraform can still delete resources or loosen IAM, and that a second AI reviewer adds an opinion, not a guarantee. The controls are mechanical:

- Export the plan as JSON and fail on out-of-scope resources; block Delete and require approval for Replace.
- Run fmt, validate, TFLint, Checkov, and plan-time policy identically in local runs and CI.
- Deny the agent merge, apply, state-write, CI, and policy-edit rights.
- Have a separate CI identity apply the exact reviewed plan file.

For builders: this pattern carries to any agent with write access to production. Gate on the computed diff, not the generated code.
