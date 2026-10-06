---
title: "LangChain's Kubernetes SRE agent needs human approval and records every step in traces"
date: 2026-08-12
theme: agentic-rca
evidence: [6a2c44f62f58bd05]
---
LangChain built an **autonomous SRE agent for Kubernetes** on Deep Agents. It requires **human approval before applying a change**, and every step, tool call, and decision is captured in LangSmith traces and covered by evals.

The trace is what a human reviews before the agent acts, not only what an engineer replays afterward.
