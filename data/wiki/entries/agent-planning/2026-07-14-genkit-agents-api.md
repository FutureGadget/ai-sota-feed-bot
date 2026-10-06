---
title: "Google's Genkit Agents API packages the loop, with detached turns and interruptible tools"
date: 2026-07-14
theme: loop-as-infrastructure
evidence: [4b81c55e5bad6a95]
---
Google released the **Genkit Agents API** in preview for TypeScript and Go. It packages message history, the tool-call loop, streaming, and state persistence behind one `chat()` interface.

Two primitives matter for planning. **Detached turns** let an agent keep working after the client disconnects. **Interruptible tools** add human-in-the-loop approval mid-plan, with anti-forgery validation on resume. "Ask vs. proceed" gets a framework-level mechanism instead of a bespoke one.
