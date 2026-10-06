---
slug: structured-output-tool-suppression
title: "Why does forcing structured output make my agent stop calling tools?"
question: "Why does forcing structured output make my agent stop calling tools?"
summary: "Enabling JSON Schema constraints and tool calling together can silently suppress tool calls in open-weight models: the schema compiles into a token mask that makes tool-call tokens unreachable, and it passes any test that checks the two capabilities separately."
status: active
cluster: tool-use
updated: 2026-10-06
audience: "strong-software-engineer"
related_topics: [tool-use, mcp, agent-evaluation]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: constrainttax-2026-tool-suppression
    kind: benchmark-result
    title: "Constraint Tax in Open-Weight LLMs: An Empirical Study of Tool Calling Suppression Under Structured Output Constraints"
    url: "http://arxiv.org/abs/2606.25605v1"
    added: 2026-07-03
    note: "With Tool Calling and JSON Schema constraints enabled together, multiple open-weight model families stop invoking tools while keeping high schema compliance; each capability works when tested alone. Traces the cause to schema grammars compiled into token masks that make tool-call tokens unreachable. Proposes Constraint Priority Inversion as a behavioral hypothesis, not a verified internal mechanism. Training-free Transparent Two-Pass Execution (unconstrained tool calls, then schema enforcement) restores tool invocation."
  - id: structured-output-tool-suppression-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-07-03
    note: "For agent builders, tool calling and structured output are usually validated as separate features. The combination needs its own explicit test, because a model can pass both checks in isolation and still go silent on tools once both constraints are active together."
---

## Builder consequence
If your agent calls tools and must also return output matching a JSON Schema, the two constraints can collide. On several open-weight model families, enabling both makes the model quietly stop calling tools, though it calls tools fine without a schema and produces valid JSON fine without tools. Nothing errors. A downstream check for "is this valid JSON" never notices.

## Short answer
Tool Calling and JSON Schema constraints each work alone. Together, multiple open-weight models show Tool Suppression: schema-valid output, no tool calls. The cause is in the decoder, not the model's reasoning: the schema is compiled into a grammar that masks which tokens are legal at each step, and that mask can make tool-call tokens unreachable. A training-free fix exists: run tool calling and schema enforcement as separate passes.

## Builder model
Treat tool calling and structured output as two constraints on one decoding process, not two features you can validate in separate suites. Grammar-based schema enforcement does not discourage disallowed tokens; it removes them. If a tool-call sequence is not in the schema's grammar, the model has no path to emit it, whatever it would otherwise choose. The bug hides behind two capabilities that each look correct alone.

## Mechanism
**Constrained decoding removes options.** Schema enforcement compiles the JSON Schema into a grammar (often a finite-state or pushdown structure). At each step, the next-token distribution is masked to tokens that keep output on a legal path. That is what makes structured output a guarantee rather than a request.

**Joint constraints can leave no path to a tool call.** The Constraint Tax study reproduces this across multiple open-weight model families: with both constraints active, the compiled grammar makes tool-call tokens unreachable, not merely unlikely. The suppression appears only on the joint decode.

**The interpretation is a hypothesis.** The paper's Constraint Priority Inversion idea, that schema satisfaction dominates action selection under multiple constraints, is offered as a behavioral account, not a verified internal mechanism. The token-masking finding is the established part.

**Decoupling sidesteps the conflict.** Transparent Two-Pass Execution generates reasoning and tool calls unconstrained, then applies the schema in a second pass that formats or validates the response. Tool invocation returns and the structured-output guarantee stays, with no retraining.

## How to apply
- **Test the combination.** Add a case that exercises tool calling with your production schema or response-format constraint active, not two suites that each pass alone.
- **Look for silent suppression.** A schema-valid response with zero tool calls where one was clearly warranted is the signature. It will not throw or raise your error rate.
- **Do not prompt around it.** Telling the model to "remember to use tools" cannot unlock a token the decoder structurally blocks.
- **Decouple before retraining.** Run tool selection and tool calls unconstrained, then enforce the schema separately, before fine-tuning or dropping structured output.
- **Re-check after model, SDK, or serving-stack upgrades.** The interaction is a serving-stack detail and can change without any prompt or schema change.

## Failure modes
- Validating tool calling and structured output in separate suites, where this failure is invisible.
- Discovering suppression only when someone notices missing tool activity downstream.
- Rewriting prompts or few-shot examples to encourage tool use when the decoder has no legal path to the tool-call token.
- Citing Constraint Priority Inversion as a proven cause rather than the paper's hypothesis.
- Fine-tuning to fix a decoding-time interaction that a two-pass setup resolves at inference.

## Related
See [tool use](/topic/tool-use) for tool-integration failure modes, [MCP](/topic/mcp) for standardized tool interfaces, and [agent evaluation](/topic/agent-evaluation) for why joint-capability tests belong in the eval suite.
