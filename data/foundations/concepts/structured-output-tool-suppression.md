---
slug: structured-output-tool-suppression
title: "Why does forcing structured output make my agent stop calling tools?"
question: "Why does forcing structured output make my agent stop calling tools?"
summary: "Turning on JSON Schema constraints and tool calling at the same time can silently suppress tool calls in open-weight models — the schema is compiled into a token mask that makes tool-call tokens unreachable during decoding, and it passes any test that checks the two capabilities separately."
status: active
cluster: tool-use
updated: 2026-07-03
audience: "strong-software-engineer"
related_topics: [tool-use, mcp, agent-evaluation]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: constrainttax-2026-tool-suppression
    kind: benchmark-result
    title: "Constraint Tax in Open-Weight LLMs: An Empirical Study of Tool Calling Suppression Under Structured Output Constraints"
    url: "http://arxiv.org/abs/2606.25605v1"
    note: "Reports a reproducible phenomenon: when Tool Calling and JSON Schema constraints are enabled simultaneously, multiple open-weight model families stop invoking tools despite maintaining high schema compliance, while tool execution and schema compliance both work fine when tested independently. Traces the cause to JSON Schema constraints being compiled into grammar-based token masks that make tool-call tokens unreachable during decoding, proposes this as the Constraint Priority Inversion (CPI) hypothesis (explicitly framed as a behavioral hypothesis, not a verified internal mechanism), and shows a training-free Transparent Two-Pass Execution strategy — generate tool calls unconstrained, then separately enforce the schema on the response — restores tool invocation without retraining."
  - id: structured-output-tool-suppression-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "For agent builders, tool calling and structured output are usually validated as separate features; this finding means the combination needs its own explicit test, because a model can pass both checks in isolation and still go silent on tools the moment both constraints are active together."
covers_evidence:
  - constrainttax-2026-tool-suppression
  - structured-output-tool-suppression-editorial-synthesis
---

## Builder consequence
If your agent both calls tools and is forced to return a response matching a JSON Schema — a common pattern once you want a fixed output contract downstream code can parse — those two constraints can interact badly. On several open-weight model families, enabling both at once causes the model to quietly stop calling tools, even though the same model calls tools fine with no schema and produces schema-valid output fine with no tools. Nothing errors. The response just stops containing tool calls, and a downstream system that only checks "is this valid JSON" will never notice.

## Short answer
Tool Calling and JSON Schema constraints, tested independently, both work. Tested together, multiple open-weight models exhibit Tool Suppression: they keep producing schema-valid output but stop invoking tools. The cause is implementation-level, not a reasoning failure — schema constraints are compiled into a grammar that masks which tokens are legal at each decoding step, and that mask can make tool-call tokens unreachable. A training-free fix exists: decouple the two passes instead of asking one constrained decode to satisfy both.

## Builder model
Treat "tool calling" and "structured output" as two constraints imposed on the same decoding process, not two independent features you can validate in separate test suites. Constrained decoding (grammar-based JSON Schema enforcement) works by restricting, at every token, which continuations are even legal — it doesn't rank or discourage the disallowed tokens, it removes them from consideration entirely. If a tool-call token sequence isn't part of the schema's grammar, the model has no path to emit it, regardless of what the underlying policy would otherwise choose. This is a token-masking interaction bug hiding behind two capabilities that each look correct on their own.

## Mechanism
JSON Schema enforcement is typically implemented as constrained decoding: the schema is compiled into a grammar (often a finite-state or pushdown structure), and at each decoding step the model's next-token distribution is masked down to only the tokens that keep the output on a path the grammar allows. This is what makes structured output reliable — it's an implementation-level guarantee, not a request the model can decide to ignore.

The paper reproduces a specific interaction failure of this mechanism: when tool calling and JSON Schema constraints are active simultaneously, the compiled grammar can leave no legal path to a tool-call token, so tool-call tokens become unreachable during decoding — not merely unlikely. Evaluated independently, both capabilities test out fine: the model calls tools correctly with no schema active, and produces valid schema-conforming output with no tools active. The suppression only appears once both constraints are enforced on the same decode.

The paper frames the interpretation carefully. It proposes Constraint Priority Inversion (CPI) — the idea that schema satisfaction ends up dominating action-selection when multiple constraints apply at once — as a hypothesis consistent with the observed behavior, explicitly not a verified internal mechanism. The token-masking explanation is the implementation-level finding; CPI is the paper's best behavioral account of why it happens that way.

The proposed mitigation, Transparent Two-Pass Execution, sidesteps the interaction instead of resolving it inside a single constrained decode: generate reasoning and tool calls unconstrained in the first pass, then apply the JSON Schema constraint in a second pass that formats or validates the response. Decoupling the two passes restores tool invocation while keeping the structured-output guarantee, with no retraining required.

## Evidence
- Benchmark/result-backed: the Constraint Tax paper reproduces Tool Suppression across multiple open-weight model families and deployment settings through controlled experiments, isolates the cause to grammar-based token masking making tool-call tokens unreachable under joint constraints, and validates that Transparent Two-Pass Execution restores tool invocation without retraining.
- Editorial inference: because tool calling and structured output are normally built and tested as separate features, the combination is a blind spot that a project's existing test suite is unlikely to catch on its own.

## How to apply
- **Test the combination, not just the parts.** Add a test case that exercises tool calling with your production JSON Schema (or response-format) constraint active at the same time, not two separate suites that each pass in isolation.
- **Watch for silent suppression, not errors.** A schema-valid response with zero tool calls where a tool call was clearly warranted is the signature to look for — it won't throw, fail validation, or show up in a generic error rate.
- **Don't try to prompt your way out of it.** If suppression is implementation-level (a token-masking artifact of joint constrained decoding), no amount of instructing the model to "remember to use tools" fixes a token it structurally cannot emit.
- **Prefer decoupling over retraining.** Try a two-pass approach — let tool selection and tool-call generation happen unconstrained, then separately enforce the output schema — before reaching for fine-tuning or dropping structured output entirely.
- **Re-check after any model, SDK, or serving-stack upgrade.** Whether constrained decoding and tool calling interact this way is an implementation detail of the serving stack, so a change to any of those components can reintroduce or change the suppression behavior even if your prompt and schema didn't change.

## Failure modes
- Testing in isolation: validating tool calling and structured output in separate test suites, which is exactly the setup where this failure is invisible.
- Silent regression: no error, no failed validation — just an agent that stops calling tools once both constraints are live, discovered only when someone notices missing tool activity downstream.
- Misdiagnosing it as a reasoning problem: rewriting prompts or few-shot examples to "encourage" tool use when the actual blocker is that the constrained decode has no legal path to the tool-call token.
- Overclaiming the mechanism: treating Constraint Priority Inversion as a proven internal cause rather than the paper's own stated hypothesis — the token-masking finding is what's established; CPI is the interpretation.
- Reaching for retraining first: fine-tuning to "fix" a decoding-time constraint interaction that a training-free two-pass decoupling can resolve at inference time.

## Related
See [tool use](/topic/tool-use) for the broader set of failure modes in connecting agents to real tools, [MCP](/topic/mcp) for how tool interfaces are standardized, and [agent evaluation](/topic/agent-evaluation) for why joint-capability tests like this one need to be part of an agent's eval suite, not just its unit tests.
