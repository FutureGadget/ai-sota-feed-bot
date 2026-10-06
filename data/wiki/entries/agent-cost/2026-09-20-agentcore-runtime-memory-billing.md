---
title: "New AgentCore runtime bills for memory actually used, with ~2s P75 cold starts"
date: 2026-09-20
theme: caching-and-serving
evidence: [b81a99111a5a8671]
---
Amazon Bedrock AgentCore's new runtime **pages memory in on demand and reclaims it when a session idles**, instead of billing the full container for the session's lifetime. Snapshotting a warmed environment holds **P75 cold start near 2 seconds** from a 200MB to a 2GB image, versus 5.4-30 seconds before.

The per-GB rate is higher, but most agents bill lower overall because they stop paying for idle memory. It applies "pay for behavior, not held capacity" to the runtime, not just the model call.
