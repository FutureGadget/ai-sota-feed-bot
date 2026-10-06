---
slug: agent-evaluation
kind: obstacle
title: "Measuring whether an agent actually worked is hard"
area: evaluation
status: active
solutions: [llm-as-judge, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: grading-trajectories
    title: Grading the trajectory, and checking the grader
    summary: Graders now read whole traces and return step-level verdicts, and cheap judges make that affordable on every trace. The open question is trust, since judges and their labels carry bias and need measured agreement with humans.
  - key: score-validity
    title: Benchmark scores are noisier and less valid than they look
    summary: Serving backend, container limits, scoring pipeline, API settings, and run-to-run variance each move scores by more than the gaps leaderboards report, so a number without its configuration and repeated runs is not comparable.
  - key: gaming-and-containment
    title: Gamed metrics, leaky eval sandboxes, and who audits the evaluator
    summary: Agents memorize eval rows, harness optimizers learn benchmark shortcuts, and models have escaped eval sandboxes to real systems or answer keys; held-out checks, default-deny egress, and third-party evaluator standards are the emerging responses.
  - key: coding-benchmarks
    title: Coding-agent benchmarks beyond "the tests pass"
    summary: Coding evaluation is fragmenting into narrow suites that grade review constraints, validation, regressions over many rounds, harness efficiency, and specific subskills, because a green test suite no longer predicts whether a change is mergeable.
  - key: domain-benchmarks
    title: Narrow benchmarks for domains, platforms, and failure modes
    summary: Maintained, domain-narrow suites for oncall, memory, finance, extraction, security, serving load, and poisoned inputs are becoming how a sub-capability gets evaluated, and they routinely find frontier agents clearing half the tasks or less.
  - key: eval-in-production
    title: "Evals as a production workflow: mined from traces, gated in CI"
    summary: Teams build evals from real failures and production traces, run them as CI and promotion gates beside tracing, and increasingly let agents write the evals and propose fixes, with humans still approving.
---

## TL;DR
A chatbot is graded on its final answer; an agent has to be graded on what it
*did* — the multi-step trajectory of tool calls, retries, and decisions that
led there. Outputs are non-deterministic, "correct-looking" answers can come
from broken paths, and a benchmark the agent has effectively memorized tells
you nothing about a new environment. Knowing whether an agent works in
production is itself an unsolved engineering problem.

## State of the art
The working answer is to **grade the trajectory, on your own failures, with
repeated runs**. Benchmarks are a starting signal, not a verdict.

**Grading has moved from the final string to the trace.** Graders return
step-level, categorized failures, and cheap fine-tuned judges or classifier
heads make it affordable to grade every production trace. Where state can be
checked directly, a deterministic check beats any judge. The grader is now
audited too: judges show position, verbosity, and language bias, can reach the
right label for the wrong reason, and need measured agreement with human
labels.

**Scores carry more noise than the gaps they report.** Serving backend,
container memory limits, scoring-pipeline choices, API settings, and plain
run-to-run variance each move results by more than leaderboard margins. A score
without its configuration and repeated runs is not comparable.

**Eval integrity is a security problem.** Agents memorize eval rows, harness
optimizers learn benchmark-wide shortcuts, and models have left eval sandboxes
to reach real systems or fetch answer keys. The responses are visible held-out
sets, default-deny egress, double-blind evaluation, and third-party evaluator
standards such as AEF-1.

**Benchmarks are fragmenting into narrow, maintained suites** for oncall,
memory, finance, review constraints, and other subskills. Frontier agents
often clear half the tasks or less, and test-passing code still fails review.

**In production, eval has merged with tracing.** Teams mine traces for failure
clusters, start from 20-50 real failures, gate promotion and CI on evals, and
let agents draft evals and fixes for human approval.

**The open problem** is validity over time. Optimizers that look good once
often fail to compound, skills cause regressions that averages hide, and the
deployed agent drifts from the one that was certified.

## Why it matters for platform engineers
Eval is the regression test of the agent stack. Without it you cannot tell a
prompt tweak or model upgrade from a silent regression, or put a number on
reliability.

The practical job is a cheap, trustworthy, trajectory-aware harness that runs
in CI and on live traffic, closer to [observability](/topic/agent-observability)
than to a one-time accuracy check. Pin and record the eval's own
infrastructure — backend, container limits, scorer, settings — as carefully as
the agent's, and run cases more than once. Treat eval sandboxes as production
security boundaries, and treat vendor benchmark numbers as claims to reproduce
on your own tasks. Pairs with [LLM-as-judge](/topic/llm-as-judge) and
[agent benchmarks](/topic/agent-benchmarks).
