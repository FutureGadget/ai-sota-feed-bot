---
title: "HiveTraceGuard-Pro: a 0.6B guardrail for Russian and English injection and obfuscation"
date: 2026-09-04
theme: model-defenses
evidence: [2e814e5a70146cc1]
---
HiveTraceGuard-Pro is a 0.6B generative guardrail, LoRA-tuned from Qwen3-0.6B, that detects prompt injection, jailbreaks, and adversarial obfuscation in Russian and English. The authors built it because existing guardrail reports give **little evidence on Russian injection or Russian surface obfuscation**.

If your users don't write in English, don't assume an English-tested guardrail's numbers carry over. Test guardrails on the languages your agent actually receives.
