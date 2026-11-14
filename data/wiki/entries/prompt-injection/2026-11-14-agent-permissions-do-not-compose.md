---
title: "Three agents that each obey their tool permissions can still leak private data together"
date: 2026-11-14
theme: agent-authorization
evidence: [89f7bd12a1554243]
also: [multi-agent]
---
A worked example shows per-agent permissions are not a system policy. A Writer can only file tickets, a Reader can only query customer records, and a Sender can only reply to the ticket's verified address. A model orchestrator routes between them.

An attacker with a valid customer account asks for a "resend" of a report listing the ten largest accounts and their balances. The Writer files it, the orchestrator hands it to the Reader, and the Sender mails the result to the attacker. No agent exceeded its own permissions.

For builders: authorization has to follow the data across handoffs. Check where an output may flow, based on its provenance, at the point it leaves the system, not only what each agent may call.
