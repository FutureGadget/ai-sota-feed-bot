---
title: "Shopify's gisting compresses a 6,000-token system prompt into 1,500 learned tokens"
date: 2026-09-05
theme: less-work-per-step
evidence: [be54aebcc77405a5]
---
Shopify trains learned **"gist" tokens** to reproduce a long system prompt's behavior: a teacher runs with the full prompt, a student learns the gist tokens by minimizing KL divergence between outputs, and the compact tokens replace the prompt at serving time.

On the Sidekick GraphQL agent the prompt shrank from about 6,000 tokens to 1,500 while holding quality. **End-to-end latency fell from 6.8s to 4.2s**, time to first token from 438ms to 354ms, and throughput rose from 20.2 to 23.4 queries/sec, enough to cut the GPU allocation for the same load. Spend side: [agent cost](/topic/agent-cost).
