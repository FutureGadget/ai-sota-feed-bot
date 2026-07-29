---
slug: agent-skill-regressions
title: "Why do reusable skills sometimes make an agent worse?"
question: "Why do reusable skills sometimes make an agent worse?"
summary: "Grading a procedural skill by average task-success improvement hides its cost: the best-performing skills win mainly by regressing less on tasks the agent already solved, not by solving more — and most regressions trace to the skill changing behavior it was never meant to touch."
status: active
cluster: tool-use
updated: 2026-07-29
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
    note: "Compares agents with and without a procedural skill across nearly 6,000 runs spanning two office-automation benchmarks and three model harness stacks. Splits outcomes into a regression (a task the agent solved without the skill but fails once the skill is added) versus a residual failure (a task that fails both with and without the skill). Finds the best-performing skills win primarily by regressing less, not by gaining more, and identifies three regression causes: skill description osmosis (the skill changes behavior just by being present in context, even when never invoked), grounding displacement (the skill's prescribed procedure overrides how the agent reads its inputs), and verification displacement (the procedure suppresses checks the agent would otherwise run on its own outputs). Analyzing persistent (residual) failures finds the same pattern in reverse: existing skills overemphasize procedural guidance, the stage least often responsible for failure, while under-supporting grounding and verification, the stages that cause most remaining errors."
  - id: story-89a606f362d88b4e-regression-tax
    kind: story
    sid: 89a606f362d88b4e
covers_evidence: [regression-tax-2026-skills, story-89a606f362d88b4e-regression-tax]
---

## Builder consequence
If you ship a procedural skill (a step-by-step playbook injected into an agent's context) and only track average task-success rate, you can ship a net regression without seeing it. A skill that fixes ten tasks and quietly breaks eight tasks the agent used to pass looks like a solid win on the aggregate number, but eight users just watched something that worked stop working.

## Short answer
Average success-rate improvement hides that skills cut both ways. Splitting outcomes into regressions (previously-passing tasks that now fail) and residual failures (tasks that never passed either way) shows the best skills mostly win by regressing less, not by solving more. Regressions cluster into three specific mechanisms, and the same three areas — procedural guidance, grounding, and verification — also explain most of what's left unsolved.

## Builder model
Treat a skill as a change to the agent's whole context, not a subroutine that only runs when invoked. A skill sitting in context can shift behavior on tasks that never call it, override how the agent reads its own inputs, and quietly turn off checks the agent would have run anyway. None of that shows up if you only measure "did the task pass," because a pass/fail count doesn't distinguish a task that was already broken from one your own change just broke.

## Mechanism
The study runs agents with and without a candidate skill across nearly 6,000 tasks, two office-automation benchmarks, and three harness stacks, then buckets every outcome change into one of two categories: a **regression** (solved without the skill, failed with it) or a **residual failure** (failed either way). This decomposition is the whole point — it separates "the skill didn't help" from "the skill actively broke something that worked."

Three mechanisms explain most regressions:

- **Skill description osmosis** — the skill's presence in context changes agent behavior even on turns where the agent never invokes it. The text doesn't have to run to have an effect.
- **Grounding displacement** — the skill's prescribed procedure overrides how the agent interprets its actual inputs, so the agent follows the recipe instead of what's in front of it.
- **Verification displacement** — the procedure supplies its own sense of "done," which suppresses the output checks the agent would otherwise perform.

Looking at residual failures (tasks that still fail with the skill) turns up a matching imbalance rather than a different problem: existing skills over-invest in procedural guidance, the stage the study finds is least often the actual cause of failure, while under-supporting grounding and verification, the stages responsible for most of what's left unsolved.

## Evidence
Benchmark/result-backed: nearly 6,000 runs across two office-automation benchmarks and three harness stacks, with outcomes decomposed into regressions vs. residual failures rather than reported as a single success-rate delta. The paper reports the direction and mechanism of the effect (regressing-less beats gaining-more among top skills; three named regression causes) without publishing a specific percentage for how much of the improvement each mechanism explains — treat the mechanism finding as established and any percentage as unstated by the source.

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
