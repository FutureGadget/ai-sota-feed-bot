---
slug: agent-benchmarks
kind: solution
title: "Agent benchmarks: fixed tasks that exercise real tool use"
status: active
obstacles: [agent-evaluation]
related_storylines: []
evidence: []
updated: 2026-11-25
themes:
  - key: trusting-the-score
    title: "What a score measures: model, harness, or noise"
    summary: Grader bugs, overspecified tests, leaked test sets, harness choice, and run-to-run noise can each outweigh model differences; audited graders, end-state diffs, replays, and paired trials are how scores earn trust.
  - key: own-workload
    title: Benchmarking on your own tools and real work
    summary: Public leaderboards overstate out-of-distribution performance; suites built from your own tools, real sessions, and held-out environments predict production better, and authoring them is getting cheaper.
  - key: domain-suites
    title: Domain-specific suites mined from real work
    summary: New suites target one job at a time (Java migration, Stripe integrations, AWS operations, Rails, code review, scientific imaging) and keep finding domain-specific failures, often in validation rather than code generation.
  - key: adversarial-and-security
    title: Adversarial tools, poisoned inputs, and security
    summary: "Benchmarks now test the failure path (multi-turn social engineering, split-screen harm, destructive chores, injection-seeded replica webs), but their own verdicts need audits: miscounted attacks and seed-sensitive scores are documented."
  - key: long-horizon-and-subsystems
    title: Long horizons and subsystem diagnostics
    summary: Long-horizon suites show final-answer scores overstate success, while subsystem benchmarks (memory, knowledge conflicts, root-cause reasoning, coordination) grade the inner process so a regression can be localized.
---

## TL;DR
Pin down a fixed set of tasks with known good outcomes and run agents against
them repeatedly. Unlike model benchmarks, agent benchmarks have to exercise
*tool use and multi-step trajectories* (booking, querying, fixing,
coordinating), so they double as integration tests for the whole agent, not
just the model.

## State of the art
Agent benchmarks score the trajectory and the end state, not only the final
answer, and the newest problem is that the grader itself is often wrong.

**Check the grader before the leaderboard.** A teardown of 12 public evals
found graders failing valid work in eight. Overspecified tests fail correct
fixes in an estimated 23% of SWE-bench Verified and 35% of Pro tasks. Silent
logging bugs reorder leaderboards, and test sets now leak into base models.
Credible suites diff the whole end state, audit verdicts, and publish
trajectories.

**The harness and the noise are part of the measurement.** The same model
gains in one harness and loses in another, and run-to-run variance can exceed
the gap between models. Treat a harness change like a model change: hold the
model fixed, run paired, repeated trials, and test against a measured noise
floor.

**Public scores transfer poorly.** Leaderboard leaders degrade in unfamiliar
environments, so the strongest signal comes from suites built on your own
tools, data, and load, such as live Postgres under traffic. A preregistered
local-agent study found no uplift at all.

**Adversarial suites now grade the failure path.** Suites test social
engineering over many turns, harm split across benign screens, deletion
chores that break servers, and injections hidden in realistic replica webs.
Their verdicts are fragile too: AgentDojo miscounted 433 successful attacks
as failures, and changing only a hash seed flipped up to 17% of one agent's
security verdicts.

**Long horizons widen the spread.** Given 36 hours and 8 H200s to build an
inference server, the best agent beat the baseline in 71% of runs and the
next in 24%; short coding suites do not show a gap that wide. Subsystem
benchmarks localize what broke.

**The open problem is validity.** A score is a claim about one task set,
grader, harness, and seed. Until graders are audited as routinely as models,
a benchmark delta is a hypothesis, not a result.

## Trade-offs
A fixed benchmark is reproducible and cheap to re-run, but it is a static
target: agents over-fit to it, it goes stale as tools change, and "passing"
can mean "memorized the distribution."

A benchmark built on your own tooling is more predictive but is real work to
author and maintain. Small task sets have high variance: swapping a few tasks
out of a ~100-task set can flip which model ranks first, so a single number is
a claim about that task set, not a general fact about the model.

Best as a regression gate that catches known failures. Complement it with
[LLM-as-judge](/topic/llm-as-judge) on live traces for the open-ended cases a
fixed suite can't enumerate.

## Why it matters for platform engineers
Agent benchmarks are the CI gate of the agent stack: a fixed suite you run on
every prompt, model, harness, or tool change to catch regressions before users
do.

The leverage is building it from *your* environment and tools, because public
leaderboards systematically overstate how an agent will do on your workload.
Budget the upkeep and repeated runs too: a benchmark is only useful while it
still resembles production and its noise is smaller than the change you are
trying to detect.
