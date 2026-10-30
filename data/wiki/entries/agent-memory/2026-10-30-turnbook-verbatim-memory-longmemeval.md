---
title: "Verbatim local memory reports 91.8% on LongMemEval from 3.1k tokens per question"
date: 2026-10-30
theme: local-first-stores
evidence: [fc08589671123b66]
---
Turnbook, a single-repo Show HN project, stores agent conversations word for word and spends **zero model tokens on saving**, unlike tools that run an LLM over transcripts at write time. It self-reports 88.8% on LongMemEval_S, and 91.8% when retrieval is capped at 3.1k tokens of memory per question (v0.10.0). The same answer model (gpt-5-mini), prompt and gpt-4o judge were used across compared systems; the post credits an embedding-model change for the token cut.

All numbers are self-reported and unreplicated. The design choice is the takeaway: move cost from write time to retrieval, and keep raw text so nothing is lost to summarization.
