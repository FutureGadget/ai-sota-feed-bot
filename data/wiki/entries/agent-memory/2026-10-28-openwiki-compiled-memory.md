---
title: A compiled, claim-linked wiki beat search roughly 5x on cross-source questions
date: 2026-10-28
theme: architectures
evidence: [b017db0483658dfc]
---
LangChain tested OpenWiki, its open-source wiki compiler, as an agent memory layer on a synthetic insurance library (111 documents, 972 facts, with outdated versions and contradictions mixed in). On questions spanning several sources, the wiki-equipped agent was roughly **5x** more accurate than keyword search alone; adding an evidence graph gave a further 27% and doubled citation consistency (vendor-reported, synthetic corpus).

Each wiki statement is a claim tied to hashed source lines. When the lines change, the hash flags the claim without a model call, and only flagged claims go to a model for revision or retraction. For builders, this is a cheap, deterministic staleness check for memory built from policy-style documents.
