---
title: "KDDI built its consumer RAG app Buffmee on Google's ADK to balance quality and response time"
date: 2026-09-09
theme: retrieval-architecture
evidence: [8a20aa410b6035c1]
---
KDDI, a major Japanese carrier, built **Buffmee**, a consumer RAG app that grounds answers in **over 100 sources** including books, magazines, and web media, on Google's Agent Development Kit. The design goal was high generation quality with fast responses across diverse media types.

At consumer scale the quality-versus-latency budget drives the retrieval architecture itself. See [agent latency](/topic/agent-latency) for the serving side.
