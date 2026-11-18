---
slug: prompt-injection-enforcement
title: "Why can't a better prompt or detector stop prompt injection in a tool-using agent?"
question: "Why can't a better prompt or detector stop prompt injection in a tool-using agent?"
summary: "Prompt injection is structural: the model reads attacker text through the same channel as the task. Defenses that ask a model to notice the attack fail under adaptive attackers; defenses that bind each write's target to the user's request, enforced in code, hold."
status: active
cluster: safety
updated: 2026-11-18
audience: "strong-software-engineer"
math_depth: intuition
related_topics: [prompt-injection, tool-use, agent-sandboxing]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: aljumaily-2026-model-as-untrusted-component
    kind: benchmark-result
    title: "Treating the Model as an Untrusted Component: Deterministic Policy Enforcement, Human Approval and Taint Tracking Against Prompt Injection in Tool-Using Agents"
    url: "http://arxiv.org/abs/2611.11571v1"
    sid: "54f1f65b7c731a1b"
    added: 2026-11-18
    note: "13 tasks, 12 tools, real runs on Qwen2.5-1.5B and 7B. The models proposed the attacker's tool call in 64% and 84% of attack episodes, but a task-bound monitor outside the model admitted only 1.3% and 7.7%. In simulation, persistent adaptive attackers drove every in-prompt guardrail stack to 100% success while the monitor held severe actions at 0.0%. Human-approval and taint results are simulation-only."
  - id: lim-2026-spillway-target-admission
    kind: benchmark-result
    title: "SPILLWAY: Separating Target Admission from Sanitization to Defend Tool-Using Agents against Prompt Injection"
    url: "http://arxiv.org/abs/2611.07222v1"
    sid: "ff6fd9e5c49f2a11"
    added: 2026-11-18
    note: "Admits an action's target only if it came from a typed field of a read-only tool result or a fixed delegation rule; a deterministic sanitizer strips instruction-like spans and keeps them as evidence, and a local judge may restore a refused call but never one targeting removed text. Templated injections redirected no actions across three backbones; mean attack success under a released RL attacker was 0.007, with near-zero added model calls."
  - id: xu-2026-caplite-write-integrity
    kind: benchmark-result
    title: "CapLite: Prompt-Injection Defense for Small Language Model Agents without Model-Written Security Artifacts"
    url: "http://arxiv.org/abs/2611.17115v1"
    sid: "c6351186c83b6a2b"
    added: 2026-11-18
    note: "CaMeL, Progent, IPIGuard and DRIFT have the agent's own model write the policy that code enforces. Across 15 open-weight models (13 at 1.7B-12B), small models wrote exploitable artifacts and CaMeL programs failed to run in up to 68% of episodes. CapLite derives policy from tool schemas, commits writes before reading tool output, and allows a write only when the user's request states its target: zero successful attacks over 13,935 AgentDojo episodes, 29.0% utility under attack, about 18% of CaMeL's tokens."
  - id: zhang-2026-task-tampering-ipi
    kind: benchmark-result
    title: "Beyond Instruction Override: Benchmarking Indirect Prompt Injection with Task-Tampering Attacks"
    url: "http://arxiv.org/abs/2611.07640v1"
    sid: "8cb3780368901295"
    added: 2026-11-18
    note: "Defines an attack by authority: content that influences a decision its source may not make. 90 cases in three environments tamper with decisions the benign task already requires. Detect-and-remove cuts objective attacks to 2.4% but leaves observation and state attacks at 9.5% and 12.1%; a tool-policy defense allows 15.4% versus 17.0% undefended, because the attack uses the expected tools with manipulated values."
  - id: xiao-2026-text-similarity-guardrail-limits
    kind: benchmark-result
    title: "Safe Resemblance, Silent Propagation: Limits of Text-Similarity Guardrails for AI Agent Safety"
    url: "http://arxiv.org/abs/2611.21520v1"
    sid: "576e1bdcfd029627"
    added: 2026-11-18
    note: "Tests DonkeyRail, a BLEU/ROUGE-L/METEOR guardrail, on a three-agent email relay. At its default threshold it misses outputs that carry out a reworded injected instruction and flags legitimate quotation and template reuse. A threshold recalibrated on one template set does not transfer to new templates."
  - id: prompt-injection-enforcement-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-11-18
    note: "Across these papers the dividing line is who decides whether an action is allowed. Defenses that ask a model (hardened prompt, detector, model-written policy) inherit the model's exposure to attacker text. Defenses that bind an action's target to the user's request or to typed, trusted fields, checked in code, do not, but they only cover write targets: value tampering inside an allowed call stays open."
---

## Builder consequence
Stop treating prompt injection as a prompt-wording or classifier problem. Assume the model **will** propose the attacker's tool call, then put a deterministic check between the proposal and execution: a write is allowed only when its target (recipient, account, path, URL) traces to the user's request or a typed field from a trusted read. Budget separately for the attacks that check cannot see: manipulated values inside calls you expected.

## Short answer
The model reads the task and the attacker's text through the same channel, so any defense that relies on the model noticing the attack fails once the attacker adapts. In one study, small models proposed the attacker's call in **64-84%** of episodes; a task-bound monitor outside the model admitted **1.3-7.7%**. Target-binding defenses enforced in code (SPILLWAY, CapLite) reported near-zero redirections. They do not stop attacks that keep the expected tool and change a value: a tool-policy defense still allowed **15.4%** of those.

## Builder model
Sort every defense by **who makes the allow decision**:

- **The model, steered by text:** hardened system prompts, spotlighting, delimiter tricks. Attacker text competes directly with them.
- **A second model:** LLM or similarity detectors. They share the first model's exposure, and similarity scores misfire on rewording and quotation.
- **Code, using a policy the model wrote:** CaMeL-style plans. Sound if the artifact is right; small models often write wrong or unrunnable ones.
- **Code, using a policy from schemas and the user's request:** target binding. The attacker's text never reaches the decision.

Only the last group survives an attacker who keeps trying.

## Mechanism
**Injection is an authority confusion, not a content problem.** A web page or email is allowed to supply data, not to decide which account receives money. The model has no reliable channel to tell those roles apart, so the fix is to make the decision somewhere the attacker's text cannot reach.

**Target admission makes provenance checkable.** SPILLWAY admits a target only if it appears in a typed field returned by a read-only tool or matches a fixed delegation rule. CapLite goes further: it fixes the set of write actions before reading any tool output and allows a write only when the user's request names the arguments that determine its target. An injected instruction can still change the model's plan, but it cannot add a write to an attacker-chosen destination.

**Detection decays under adaptation; enforcement does not.** A detector is a classifier with a threshold, and a persistent attacker searches for inputs below it. In simulation, adaptive attackers drove every guardrail stack to 100% success while the deterministic monitor held severe actions at 0%.

**The open hole is value tampering.** Task-tampering attacks keep the expected tool and recipient but change what the agent believes: a price, a state flag, a decision rule. Target binding does not inspect those values, which is why observation- and state-targeting attacks kept 9.5-12.1% success under detection and 15.4% under tool policy.

## Math intuition
Model an adaptive attacker as making `k` independent tries against a detector that misses each with probability `p`. The chance at least one gets through is `1 - (1 - p)^k`. With `p = 0.05` and `k = 50`, that is about **92%**. A detector's per-try miss rate tells you little once retries are free.

A target-binding check is different: for an action whose target is not derivable from trusted inputs, the pass probability is 0 regardless of `k`, because the check never reads the attacker's text. Its residual risk lives in the actions it allows by construction, such as an expected call with a tampered value, so measure that class separately instead of averaging it into one attack-success number.

## How to apply
- **Classify every tool as read or write**, and give each write a declared target argument.
- **Bind write targets in code:** allow only targets that appear in the user's request, a fixed allowlist, or a typed field from a read-only tool. Reject targets that appear only in free text the model read.
- **Commit the write plan before reading untrusted content** where the workflow allows it.
- **Don't let a small model write its own security policy.** Derive policy from tool schemas instead.
- **Keep detectors as telemetry,** not gates: log what they flag, never rely on them to block.
- **Require human approval for irreversible writes** whose values came from untrusted reads.
- **Test value tampering explicitly:** add eval cases where the attack keeps the right tool and target and changes a number, state, or rule.

## Failure modes
- Shipping a hardened prompt plus detector and reporting attack success from static, non-adaptive attacks.
- Gating multi-agent relays on text similarity, which misses reworded payloads and blocks legitimate quotes.
- Trusting a model-generated plan or policy without checking that it runs and constrains targets.
- Declaring the agent safe because redirection attacks fail, while tampered values flow through allowed calls.
- Letting free-text tool output populate a write target "just this once" for convenience.

## Related
See [prompt injection](/topic/prompt-injection) for the threat landscape, [why exfiltration channels survive fixes](/foundations/agent-tool-exfiltration-channels), and [MCP security control layers](/foundations/mcp-security-control-layers).
