---
title: "A training-free validate-and-repair layer recovers tool calls broken by interface drift"
date: 2026-10-19
theme: calling-reliability
evidence: [8d12f92c932c9a54]
---
Tool descriptions, argument schemas, and the candidate tool list often change after deployment while tool semantics stay fixed. A paper calls this **interface drift** and tests SchemaShield-Lite: schema validation, a candidate-set retry when the tool name is missing, and one-shot constrained repair, with no retraining.

On Qwen3.5-9B (paper-reported), BFCL-200 accuracy rises from 0.580 to 0.805 and DICE-300 from 0.717 to 0.813. It recovers 33 of 45 and 19 of 22 drift-induced failures with no observed repair harms. Naive retry does not explain the gain. Distractor tools in the candidate set cause most of the damage.

For builders: validate every call against the live schema and keep the candidate list stable.
