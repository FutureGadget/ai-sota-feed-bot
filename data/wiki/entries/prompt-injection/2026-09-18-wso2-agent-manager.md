---
title: "WSO2 Agent Manager applies identity, RBAC, and revocation to agents across frameworks"
date: 2026-09-18
theme: agent-authorization
evidence: [8ae9c1754d54b75b]
---
WSO2 Agent Manager, now generally available and open source, decouples governance from agent logic. Role-based access control, delegation, token exchange, and revocation apply to an agent's identity whatever model, framework (LangChain, CrewAI, custom), or runtime it uses. It ships **40+ built-in policies**, including PII masking and rate limiting, enforced across the agent, MCP, and LLM layers, plus a Kubernetes-native sandboxed runtime.

It is the self-hosted counterpart to a managed platform such as AgentCore.
