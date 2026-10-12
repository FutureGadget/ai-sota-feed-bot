---
title: "Spotify Ads AI enforces one agent, one package, one owner, with deterministic gates outside the agents"
date: 2026-10-12
theme: production-evidence
evidence: [fae73393a0aa4548]
also: [agent-tracing]
---
A Spotify engineer's QCon AI talk describes the Ads AI platform on Google ADK (Java). Each agent is its own Bazel package with a named owning team, a monitoring YAML (dashboards, PagerDuty), and its LLM config; one agent cannot import another unless the target's visibility allows it, so a violation is a **build failure**. Guardrails and orchestration sit in a shared layer, not inside agents. Agents own judgment (intent, ad brief, policy screening); data such as interest segments and DMA targeting comes from API tools, and anything codeable stays deterministic code.

Spotify-reported: over 70% of ads use the AI tools, ~20,000 creatives for 7,000+ advertisers. Builders can copy the ownership and compile-time boundaries.
