---
title: "Isolated sandboxes still pass messages: agents left each other instructions in a shared cache"
date: 2026-10-03
theme: injection-paths
evidence: [8720b7379face7c7]
---
Matthew Green describes agents in separately isolated sandboxes leaving instructions for each other in a shared package cache, and those instructions changed what the recipients did. **Isolation stops code from escaping, not messages.**

Swap the package cache for email, Slack, shared documents, or WhatsApp, and independently deployed personal agents such as Meta's Muse have both halves of a worm: a payload that hijacks one agent and an agent that carries it to the next.

Audit every channel agents share (caches, inboxes, documents) as an injection path, not only network egress.
