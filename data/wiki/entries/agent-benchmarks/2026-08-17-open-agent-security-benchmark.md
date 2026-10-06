---
title: "An open agent-security benchmark scores defenses on 497 attacks and 1,172 benign samples"
date: 2026-08-17
theme: adversarial-and-security
evidence: [3d4de4cad355f358]
---
An open, **tool-agnostic security benchmark** tests any HTTP-addressable classifier against 497 attacks in 13 categories (direct and indirect injection, credential exfiltration, tool abuse, system-prompt extraction, memory poisoning, supply-chain manipulation) plus 1,172 benign samples. The author publishes the attacks their own defense fails to catch.

Scoring F1, precision, and recall together means a defense that blocks everything doesn't look artificially strong. See [prompt injection](/topic/prompt-injection).
