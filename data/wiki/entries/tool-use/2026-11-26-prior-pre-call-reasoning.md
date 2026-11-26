---
title: "Tool use fades under RL when SFT traces skip reasoning before calls; deeper pre-call reasoning keeps it"
date: 2026-11-26
theme: calling-reliability
evidence: [adca41e514a08c77]
---
PRIOR studies why fine-tuned agents stop calling tools during later RL. SFT trajectories with little reasoning before each tool call lose tool use during RL. Filtering the SFT data for longer pre-call reasoning improved post-RL accuracy across benchmarks.

For builders training their own tool-use models: audit SFT traces for reasoning before each call, not just correct calls. Short call-only traces can look fine after SFT and still collapse once RL starts.
