---
title: "Coding-agent sandboxes contain code execution but don't scope the credentials inside them"
date: 2026-06-19
theme: agent-authorization
evidence: [2f585fd257ad02a4]
---
Permit.io argues that a coding-agent sandbox contains code execution but does nothing about **credential authorization**: the agent inside still holds tokens that injected instructions can use.

Sandboxing is necessary, not sufficient. Pair it with scoped, short-lived credentials so a hijacked agent inside the box can't act beyond its task. See [agent sandboxing](/topic/agent-sandboxing).
