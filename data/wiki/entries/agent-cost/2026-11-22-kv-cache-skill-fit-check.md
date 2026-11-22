---
title: "AWS KV-cache agent skill checks fit before setup and warns hit counters can look healthy on wrong answers"
date: 2026-11-22
theme: caching-and-serving
evidence: [f6e744ab21c05ceb]
also: [agent-latency]
---
AWS released an Agent Skill that walks a coding agent through adding LMCache-backed distributed KV caching to a vLLM or SGLang fleet. It first runs a fit check: the cache pays off only above a **cutover prompt length**, where loading KV state beats recomputing it, and only if prompts repeat often enough to cover the cache's cost. If GPU prefix-cache hits already exceed 90% with session affinity, it may not be needed.

Every server must share one KV hash and seed, or each writes state the others cannot find. A layout mismatch can show **healthy hit counters and wrong answers**, so verify two cache-loaded runs match. A shared cache lets one tenant infer another's prompts from response times, so isolate tenants by cache or hash ID.
