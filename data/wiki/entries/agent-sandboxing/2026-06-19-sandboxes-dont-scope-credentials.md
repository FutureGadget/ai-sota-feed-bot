---
title: "Coding-agent sandboxes contain the process but not the credentials inside it"
date: 2026-06-19
theme: credential-boundary
evidence: [2f585fd257ad02a4]
---
Permit.io's analysis argues that sandboxing a coding agent **does not solve credential authorization**. The agent inside the box still holds tokens, and injected instructions can spend them on whatever those tokens allow.

Isolating the process is not isolating its privileges. Pair every sandbox with scoped, short-lived credentials and an authorization layer that decides what each call may do.
