---
title: "Grammar-forced tokens become a second drafter, raising acceptance length for JSON and tool-call outputs"
date: 2026-11-24
theme: draft-methods
evidence: [b6559df505fa2a9e]
also: [agent-latency, tool-use]
---
Under structured outputs, speculative drafters cannot see the grammar and keep proposing invalid keys and delimiters that the verifier rejects. *Grammar-as-a-Draft* merges the drafter's proposal with the tokens the grammar engine already forces, and the verify step accepts forced tokens without computing their logits. It needs no new kernels and composes with MTP, DFlash, and n-gram drafters; the authors show longer acceptance and faster decoding in vLLM and a Rust runtime on TPU v7x. Committing canonical forced tokens does change the output distribution slightly.

For builders: tool calls and JSON responses are where agents spend many output tokens, and the grammar already knows much of them.
