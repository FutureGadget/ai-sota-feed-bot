---
title: "LiveLoRA migrates a session's KV cache across LoRA updates, about 69x faster than re-prefilling history"
date: 2026-11-24
theme: caching-and-serving
evidence: [a906191009e1abf8]
also: [agent-latency]
---
When an agent's LoRA adapter is updated mid-session, the usual fix is to re-prefill the whole history under the new adapter. *LiveLoRA* migrates only the final-block KV cache to the new version exactly. On Qwen2.5-3B-Instruct with **32 sessions of 8K tokens**, it reports about **69x** median speedup over full re-prefill.

For builders: continual adaptation of per-user or per-tenant adapters stops being a cache flush. That makes frequent adapter updates affordable for long-running agent sessions.
