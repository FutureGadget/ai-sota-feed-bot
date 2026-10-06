---
title: "KVShareArena: KV reuse outside the prompt prefix can score worse than no cache at all"
date: 2026-09-11
theme: kv-state
evidence: [38a96835bd201857]
---
Prefix caching assumes reused text sits at the start of the prompt. RAG assembles different chunks per query, and a multi-agent coordinator reads other agents' reports, so reusable text lands **mid-prompt**, at the wrong positions, sometimes from another checkpoint.

KVShareArena scores reuse methods on that case. Correcting positions alone suffices until a question needs several retrieved sources; then only methods that pay for partial re-encoding or extra training recover half to two-thirds of the gap. **An unrepaired cache can score worse than no cache**, and compression that looks harmless on one prompt falls behind plain position correction.
