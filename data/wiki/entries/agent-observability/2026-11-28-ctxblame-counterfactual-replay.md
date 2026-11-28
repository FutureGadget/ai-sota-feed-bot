---
title: "Counterfactual replay names the context chunk that caused a tool call, without asking the model"
date: 2026-11-28
theme: reading-traces
evidence: [a0f3d3f24e09f514]
also: [agent-tracing]
---
`ctxblame` records an agent's Anthropic- or OpenAI-format requests through a local proxy, then replays one step N times with pieces of context removed. It reports which chunk changed the decision. The evidence comes from replays, not the model's own explanation.

Removing a tool call also removes its result, so ablated requests stay valid. Reported causes are re-checked on fresh replays with family-wise error held at α. On a Qwen3-14B coding step, it caught three redundant carriers of one instruction that leave-one-out missed. Replays are priced, with a default $5 hard cap.

For builders: when an agent picks the wrong tool, replay that step and ablate context before you rewrite the prompt. Replays against a local vLLM server cost nothing.
