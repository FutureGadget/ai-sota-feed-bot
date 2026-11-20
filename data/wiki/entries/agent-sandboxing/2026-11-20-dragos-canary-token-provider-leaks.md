---
title: "Canary tokens in two million prompts surfaced at three compromised AI providers and inference resellers"
date: 2026-11-20
theme: credential-boundary
evidence: [6742621af555e290]
also: [prompt-injection]
---
Security firm Dragos seeded about two million prompts with unique URLs, DNS names, and AWS credentials across widely used AI services from July to November 2026, then watched where the tokens resurfaced. As summarized in a secondary report, the test found evidence of **three provider compromises**, inference-marketplace resellers reading customer prompts, and widespread failures to honor Zero Data Retention and other privacy settings.

For builders: treat every prompt as data that can leave your trust boundary, whatever the provider's retention setting. Keep live credentials out of context, and route through resellers only with the same scrutiny as any other third-party processor.
