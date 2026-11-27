---
title: "An OpenRouter provider's \"private, self-hosted\" models were often served by other providers"
date: 2026-11-27
theme: serving-runtime-drift
evidence: [2bb714fbc5927fde]
---
An independent probe of Venice, an OpenRouter provider, found its privacy label did not match where requests ran. On 2026-11-21, 14 of 18 listed image models fetched outputs from Baseten, DeepInfra, Fireworks, or Parasail. For Qwen3.5 397B, 32 of 40 test requests looped back into OpenRouter. Venice later moved that model and removed another. The author published attested probe logs; Venice's privacy page defines "private" to include partner infrastructure.

For builders: through an aggregator, the provider label does not tell you which infrastructure ran the request. Pin providers explicitly, and verify data-retention claims per model rather than per vendor.
