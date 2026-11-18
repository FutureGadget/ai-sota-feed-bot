---
title: "A hijacked Hugging Face account can swap model weights with no code change to detect"
date: 2026-11-18
theme: transitive-pinning
evidence: [5a10d07ea77b0867]
also: [prompt-injection]
---
Researchers took control of the Hugging Face account behind **Kokoro**, a text-to-speech model used in Google, NVIDIA, AMD, Intel and AWS projects, because the platform did not verify ownership. Instead of planting code, they changed only the weights so the model spoke audio that differed from its input text. Application code stayed the same, so code review and package scanners had nothing to flag.

For builders, the weights are a dependency like any other. Pin a model to a specific repository revision hash rather than a branch or `latest`, and add a behavioral check (such as a fixed golden input and output) before a new revision reaches production.
