---
title: "Lossy speculative decoding raises jailbreak and injection success faster than it costs utility"
date: 2026-10-11
theme: draft-methods
evidence: [c47efdba3284bb9f]
also: [prompt-injection, agent-latency]
---
A measurement study of lossy speculative decoding methods finds a security-utility asymmetry: as inference gets faster, jailbreak and prompt-injection attack success rises much faster than utility degrades. The authors trace the loss to early tokens proposed by the draft model.

Their fix, **SecureSD**, applies a stricter verification criterion to draft tokens at early decoding positions, and reports better security at maintained efficiency and utility (paper-reported, no deployment numbers).

For builders: if you enable lossy acceptance to buy throughput, rerun your injection and jailbreak suite on the speculative configuration, not just the base model.
