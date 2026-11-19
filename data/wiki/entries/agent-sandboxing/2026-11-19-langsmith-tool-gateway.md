---
title: "LangSmith Tool Gateway moves credentials, identity and approvals for agent tool calls into a managed layer"
date: 2026-11-19
theme: credential-boundary
evidence: [d40b37a43fa11767]
also: [tool-use]
---
LangChain launched Tool Gateway in public beta on the LangSmith Agent Platform. It is a managed tool layer that holds **credentials**, decides **whose identity** each call acts with, enforces per-agent access **policies and approvals**, and traces every action. The pitch is scheduled and event-triggered agents that run long tasks with nobody watching each step.

For builders: this joins the pattern of keeping secrets out of the agent process and brokering every call through a policy point. Evaluate it on lock-in and on whether its policies can express argument-level rules, not just tool-level allow lists.
