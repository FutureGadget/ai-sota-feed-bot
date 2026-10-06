---
slug: agent-skill-regressions
title: "Why do reusable skills sometimes make an agent worse?"
question: "Why do reusable skills sometimes make an agent worse?"
summary: "Grading a procedural skill by average task-success improvement hides its cost: the best-performing skills win mainly by regressing less on tasks the agent already solved, not by solving more — and most regressions trace to the skill changing behavior it was never meant to touch."
status: active
cluster: tool-use
updated: 2026-10-06
audience: "strong-software-engineer"
math_depth: ""
related_topics: [tool-use, agent-reliability]
related_playbook_cards: [pb-skills-regression-tax]
related_storylines: []
evidence:
  - id: regression-tax-2026-skills
    kind: benchmark-result
    title: "The Regression Tax: Decomposing Why Skills Help and Hurt LLM Agents"
    url: "http://arxiv.org/abs/2607.22520v1"
    sid: "89a606f362d88b4e"
    added: 2026-07-29
    note: "Nearly 6,000 runs across two office-automation benchmarks and three harness stacks, with and without a procedural skill. Splits outcomes into regressions (solved without the skill, failed with it) and residual failures. The best skills win mainly by regressing less. Names three regression causes: description osmosis, grounding displacement, verification displacement. Reports direction and mechanism, not per-mechanism percentages."
---

## Builder consequence
If you ship a procedural skill (a step-by-step playbook injected into an agent's context) and only track average task-success rate, you can ship a net regression without seeing it. A skill that fixes ten tasks and quietly breaks eight tasks the agent used to pass looks like a solid win on the aggregate number, but eight users just watched something that worked stop working.

## Short answer
Average success-rate improvement hides that skills cut both ways. Splitting outcomes into regressions (previously-passing tasks that now fail) and residual failures (tasks that never passed either way) shows the best skills mostly win by regressing less, not by solving more. Regressions cluster into three specific mechanisms, and the same three areas — procedural guidance, grounding, and verification — also explain most of what's left unsolved.

## Builder model
Treat a skill as a change to the agent's whole context, not a subroutine that only runs when invoked. A skill sitting in context can shift behavior on tasks that never call it, override how the agent reads its own inputs, and quietly turn off checks the agent would have run anyway. None of that shows up if you only measure "did the task pass," because a pass/fail count doesn't distinguish a task that was already broken from one your own change just broke.

## Mechanism
The useful move is to split every outcome change into a **regression** (solved
without the skill, failed with it) and a **residual failure** (failed either
way). That separates "the skill didn't help" from "the skill broke something
that worked". The Regression Tax study did this across nearly 6,000 runs and
found three mechanisms behind most regressions:

- **Skill description osmosis** — the skill's presence in context changes
  behavior even on turns where it is never invoked.
- **Grounding displacement** — the prescribed procedure overrides how the agent
  reads its actual inputs, so it follows the recipe instead of the evidence.
- **Verification displacement** — the procedure supplies its own sense of
  "done" and suppresses checks the agent would otherwise run.

Residual failures show the same imbalance from the other side: skills
over-invest in procedural guidance, the stage least often at fault, and
under-support grounding and verification, where most remaining failures start.

## How to apply
- **Score two numbers, not one.** For every candidate skill, measure tasks newly solved and previously-passing tasks now failing separately — never collapse them into a single success-rate delta before shipping.
- **Audit failures for the three named modes.** When a task regresses, check whether the skill changed behavior on a turn it wasn't invoked on (osmosis), overrode input interpretation (grounding displacement), or suppressed an output check (verification displacement) before rewriting the procedure itself.
- **Write grounding and verification steps as explicitly as the procedure.** If a skill spells out steps but leaves "check your inputs" and "check your output" implicit, it's the shape most likely to displace exactly those checks.
- **Re-test previously-passing tasks whenever a skill changes.** A skill update that only gets evaluated against its target tasks will never surface a regression on tasks outside that set.

## Failure modes
- Grading a skill by aggregate success-rate improvement, which lets regressions on previously-solved tasks hide behind gains on new ones.
- Assuming a skill only affects behavior when the agent actually invokes it, missing osmosis effects from the skill merely being present in context.
- Treating every regression as a procedure-writing problem and iterating on the steps, when the study finds grounding and verification gaps cause most of the remaining failures.
- Shipping a skill update without re-running the agent's previously-passing task set, so a new regression ships silently.

## Related
See [tool use](/topic/tool-use) for the broader set of failure modes in connecting agents to real tools, and [agent reliability](/topic/agent-reliability) for why fluent, confident-looking output doesn't imply the agent's checks are still running.
