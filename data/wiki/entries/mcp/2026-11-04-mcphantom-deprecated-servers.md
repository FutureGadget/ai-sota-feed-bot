---
title: "Coding agents install deprecated MCP servers with known vulnerabilities"
date: 2026-11-04
theme: auth-and-governance
evidence: [7bf2baae197f3346]
---
Glow Labs reports "MCPhantom": coding agents choosing to install retired MCP servers, apparently from stale training data, and leaving high-severity flaws on developer machines with no security updates. The finding is vendor-reported from the firm's own monitoring.

For builders: an agent's choice of MCP server is a supply-chain decision. Put an allowlist or registry check with deprecation status in front of installs instead of trusting the model's recall.
