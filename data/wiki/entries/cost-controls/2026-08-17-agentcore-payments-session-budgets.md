---
title: "AgentCore Payments caps what an agent spends on paid APIs per session"
date: 2026-08-17
theme: hard-caps
evidence: [2d5ee61a05111f0a]
also: [agent-cost]
---
AWS's **AgentCore Payments** middleware lets a LangChain agent pay third-party APIs directly. It signs x402-protocol payments against a **deterministic per-session budget** instead of handing the agent an open credential, and LangSmith traces every payment.

It extends "meter and cap" from model tokens to the agent's own outbound spending on the services it calls. As agents buy data and API calls, that spend needs the same per-session ceiling as token spend.
