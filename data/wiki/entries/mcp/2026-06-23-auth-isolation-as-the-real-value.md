---
title: "MCP's real value may be keeping the auth flow out of the agent's context"
date: 2026-06-23
theme: stateless-spec
evidence: [9370d60ff069b1f4]
---
A Hacker News comment by Sean Lynch, quoted by Simon Willison, argues that what MCP offers over skills or a CLI is **isolating the auth flow outside the agent's context window**, and possibly outside the harness entirely. Its idealized form might be "just an auth gateway for the API".

Read this way, MCP's durable win is credential handling, not the tool-description format. The same question returns once the stateless spec makes MCP look more like a plain API.
