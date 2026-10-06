---
title: "An open agent-security benchmark scores defenses on 497 attacks plus 1,172 benign samples"
date: 2026-08-17
theme: model-defenses
evidence: [3d4de4cad355f358]
---
An open benchmark tests any HTTP-addressable classifier against **497 attacks across 13 categories**, including direct and indirect injection, credential exfiltration, tool abuse, system-prompt extraction, memory poisoning, and supply-chain manipulation. It adds 1,172 benign samples and reports F1, precision, and recall together, so a defense that blocks everything doesn't look strong. The authors also publish the attacks their own defense fails to catch.

Include benign traffic when you evaluate a guardrail: block rate alone hides the false positives that push users to switch it off. See [agent benchmarks](/topic/agent-benchmarks).
