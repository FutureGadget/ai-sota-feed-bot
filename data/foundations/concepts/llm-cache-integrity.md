---
slug: llm-cache-integrity
title: "Why do LLM caches fail silently?"
question: "Why do prompt caches and KV caches fail without raising an error, and how do you catch it?"
summary: "Prompt caches and KV caches report success whether or not they work. Misconfigured prompt caching quietly costs money; a mishandled KV cache once leaked other tenants' data. Verify cache behavior with measured hits and canaries, not status codes."
status: active
cluster: operations
updated: 2026-10-30
audience: "strong-software-engineer"
math_depth: none
related_topics: [agent-cost, cost-controls, scalability]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: arxiv-2610-34817-cachelint
    kind: benchmark-result
    title: "Silent and Costly: Characterizing and Detecting Prompt-Caching Mis-Integration in LLM Agents"
    url: "https://arxiv.org/abs/2610.34817"
    sid: "acf14c1d41e7a5ef"
    added: 2026-10-30
    note: "Empirical study of 120 prompt-caching pull requests from 10 open-source agent systems (ICSE 2027). Mis-integrations are request-side misconfiguration or read-side usage miscount, and most fail silently with no runtime error. The CacheLint static checker reaches 0.71 precision and 0.78 recall on the 120 labeled cases, and found 32 mis-integrations across 571 projects at 0.86 precision. It led to 18 upstream fixes, one in Anthropic's official SDK."
  - id: cloudflare-2026-kv-cache-exposure
    kind: production-field-report
    title: "Cross-request KV cache exposure in the GLM-5.3 Workers AI model, and our remediation with SGLang"
    url: "https://blog.cloudflare.com/kv-cache-exposure-remediation"
    sid: "89893d5f73c77515"
    added: 2026-10-30
    note: "Cloudflare postmortem. From Aug 27 to Sep 9, 2026, 155 GLM-5.3 responses to prompts over 681,280 tokens contained other customers' data. The model's 1,048,576-token context exceeded the 681,280-token prefill KV pool. In disaggregated prefill/decode mode, SGLang replaced the oversized prompt with a placeholder instead of aborting, so decode attended over stale cache pages. Fixed by sizing the pool to about 2.04M tokens and rejecting early."
  - id: llm-cache-integrity-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-10-30
    note: "Both incidents share one shape: a cache layer whose success signal does not prove correct behavior. The cost bug returns a normal response at full price; the isolation bug returns a normal response with the wrong content. Neither trips an alert unless you measure the cache's effect directly."
---

## Builder consequence
A cache that is wired wrong still returns 200 OK. In a study of 120 prompt-caching pull requests, most mis-integrations **failed silently**: the app worked and the bill grew. At the other end, one inference-engine cache bug returned other customers' data with no error. Treat cache behavior as something you measure, not something you assume.

## Short answer
LLM caching reuses stored computation for a repeated prompt prefix. Providers cache the prefix; engines cache attention state (the KV cache) per request. Both layers skip work and both can be wrong without failing. Cost-side errors waste money; isolation-side errors leak data. The fix in each case is an explicit check on cache behavior.

## Builder model
Separate two layers and two failure types.

- **Prompt cache (provider API):** you mark or order a stable prefix. Failure is lost savings.
- **KV cache (inference engine):** the server holds per-request attention state. Failure is wrong or leaked content.

Your code owns the first layer. Your hosting provider or serving stack owns the second, unless you self-host.

## Mechanism
Prompt caching only hits when the cached prefix is byte-identical and meets provider-specific rules, such as minimum length and explicit markers. A timestamp, reordered tool list, or missing marker near the top of the prompt breaks the match. The request still succeeds at full price. Usage fields also differ by provider, so cache reads can be miscounted when you read them.

KV cache bugs are state-handoff bugs. Cloudflare's incident arose when a prompt exceeded the prefill pool. The engine substituted a placeholder, sent "transfer complete" to the decode node, and the decode node trusted that message. It attended over cache pages still holding earlier requests' data. A success message stood in for verified content.

## How to apply
- **Alert on cache-hit rate.** Log cached versus uncached input tokens per call and alert when the ratio drops after a deploy.
- **Keep the prefix stable.** Put system prompt and tool definitions first, in fixed order, and put timestamps and per-user data last.
- **Test each provider's rules.** Check minimum length, markers, and how usage is reported before trusting a savings estimate.
- **Run a canary on shared inference.** Send a unique marker with a long prompt, then confirm it never appears in other tenants' or sessions' output.
- **Match pool size to context length** if you self-host, and make over-length requests fail with an error.

## Failure modes
- **Assuming "it's enabled" means "it's working."** Without hit-rate metrics, a broken cache is invisible.
- **Trusting a transfer-complete signal** between prefill and decode without checking token counts.
- **Testing only short prompts.** The Cloudflare bug appeared only above 681,280 tokens.
- **Copying one provider's cache setup to another.**

## Related
See `/topic/agent-cost` for cost controls.
