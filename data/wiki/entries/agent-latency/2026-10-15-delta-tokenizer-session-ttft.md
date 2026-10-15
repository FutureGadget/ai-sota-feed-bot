---
title: "Tokenizing only each turn's appended text cuts agent TTFT, the CPU step KV reuse leaves behind"
date: 2026-10-15
theme: agent-traffic
evidence: [d4d5081186e81c2b]
---
Inference engines reuse the KV cache of a session's shared prefix, but the CPU front end still re-tokenizes the whole conversation each turn. Delta Tokenizer keeps the previous token sequence, re-encodes only the appended text plus a short tail, and splices at a boundary the tokenizer's splitting rules cannot move, so output stays exact.

Paper-reported results:
- About 40x faster tokenization per session turn than the Hugging Face reference.
- Inside SGLang: median TTFT down 59% at 100K tokens; agent-session P99 TTFT down 9.5x under load, 23x when long requests block the front end.

Long-session agents should profile tokenization, not only GPU time.
