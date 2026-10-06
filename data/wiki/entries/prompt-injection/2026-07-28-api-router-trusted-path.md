---
title: "Third-party API routers sit on the trusted path and can inject into coding-agent traffic"
date: 2026-07-28
theme: injection-paths
evidence: [68562210b323388b]
---
Routers that unify access across LLM providers sit between a coding agent and the upstream model and can inspect and modify every request and response. **Nothing verifies that what the router forwards matches what the provider returned**, so client-side permission checks that assume an honest transport stop working.

The SIDEL study tests four escalating tampering levels (raw response swap, appended instruction, LLM-polished injection, and a polished injection distribution-matched to the original) across four coding agents on 400 curated samples.

Treat a router as a trust boundary, not only a cost component. See [cost controls](/topic/cost-controls).
