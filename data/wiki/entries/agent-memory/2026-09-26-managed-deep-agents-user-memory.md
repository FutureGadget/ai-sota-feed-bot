---
title: "Managed Deep Agents 0.8 scopes memory to the authenticated user and denies it in group channels"
date: 2026-09-26
theme: shared-memory
evidence: [ae0a400c8192a304]
---
LangChain's **Managed Deep Agents 0.8** adds a two-tier memory config, `define_memory(agent=MemoryLayer(), user=MemoryLayer())`. User memory mounts at `/memories/user/`, keys to the caller's identity, and is allowed in one-to-one Slack DMs but **denied by default in group chats and HTTP channels**.

It pairs that with per-user credentials (OAuth across 23 services), so both what an agent remembers and what it can touch follow the caller. One user's context can't leak into another's conversation through a shared deployment.
