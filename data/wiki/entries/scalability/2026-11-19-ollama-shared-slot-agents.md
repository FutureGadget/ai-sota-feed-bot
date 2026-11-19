---
title: "Two coding agents sharing one Ollama slot waited a median 46 seconds for first token, against one second apart"
date: 2026-11-19
theme: concurrent-serving
evidence: [9521493295c710cd]
also: [agent-latency]
---
A field test ran two coding-agent sessions against one Ollama server. Sharing one slot, each waited a **median 46 seconds** for a response to start; with a slot each, about **one second**. Over half the prompt tokens the server processed were repeats.

The cause is the agent loop: every tool result triggers another, longer prompt, and when two sessions alternate on one slot each evicts the other's cached prefix, so the server re-prefills history it already had. Hybrid models lose their place more easily. For builders running local inference: give each concurrent agent its own slot (parallelism setting) before adding hardware, and measure prefix reuse, not just tokens per second.
