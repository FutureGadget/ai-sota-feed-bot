---
title: "A certified confidence test skipped a verifier agent on 39.9% of questions while keeping 12.55 of 12.80 points"
date: 2026-11-19
theme: when-it-pays
evidence: [42ddde99a4b6a022]
also: [agent-latency]
---
A receiver agent reads its own confidence without a helper's message, and a finite-sample test certifies a threshold where at most **5%** of skipped answers change; if no threshold passes, it keeps communicating. In prospective tests with rules fixed in advance, it skipped a three-agent system's verifier on **39.9%** of sealed questions, keeping **12.55 of its 12.80-point** gain.

Two cautions: content-free control messages reproduced a median 76% of the oracle gain, so "messages help" is weak evidence, and certification held on SQuAD but not GSM8K. For builders: treat each inter-agent message as optional and measure whether it changes answers before paying its latency.
