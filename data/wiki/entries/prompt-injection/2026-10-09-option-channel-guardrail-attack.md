---
title: "Typed-decision guardrail models are easily flipped to fail-open, so they should not be the gate"
date: 2026-10-09
theme: model-defenses
evidence: [0f0c80587e932ad4]
---
A paper tests seven open-weight "typed decision" models as agent guardrails (read a tool call or message, return a probability over allow/block options). Allow-or-block accuracy on injection, jailbreak, and toxicity screening ranged **36% to 72%** against a 50% chance level. Six lines of irrelevant server-log text raised one gate's fail-open rate from 0% to 63%; renaming the permissive option raised it to 93-100% on four models. Every defense tested was defeated, and escalating low-confidence decisions did not help.

For builders: use such models to shrink the review queue, not to decide. A deterministic rule over typed policy fields reached 100% accuracy on all six policies.
