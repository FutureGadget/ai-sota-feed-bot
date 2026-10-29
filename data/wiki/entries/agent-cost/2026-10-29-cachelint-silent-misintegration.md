---
title: "Prompt-caching bugs in agent code fail silently; CacheLint found 32 across 571 projects"
date: 2026-10-29
theme: caching-and-serving
evidence: [acf14c1d41e7a5ef]
---
An empirical study of 120 prompt-caching pull requests across 10 open-source agent systems found mis-integrations on both the request side (misconfiguration) and the read side (miscounted cache usage). Most fail silently: nothing errors, the bill is just higher.

The authors' CacheLint (paper-reported) uses CodeQL to find caching call sites and checks preconditions against a dated provider capability oracle or an LLM guard. It scored 0.71 precision and 0.78 recall on the 120 labeled cases, and 0.86 precision on 32 new findings across 571 projects, leading to 18 upstream fixes including one in Anthropic's SDK. Audit cache-hit tokens in billing data, not just code.
