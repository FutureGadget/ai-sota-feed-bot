---
slug: agent-benchmarks
kind: solution
title: "Agent benchmarks: fixed tasks that exercise real tool use"
status: active
obstacles: [agent-evaluation]
related_storylines: [deep-research]
evidence: [432c23c0dd1c00f1, f07b6a3f3f344020, 55809dc9368e7936, 8f76e67ad854a6c0, 64ad8e685ed41a9b, 3abcf8c08cb66506, e214c4d6ded906fa, 4500a2b43ff7ed73, ebc3627096b332c8, 45c05959600cf833, 72d3e39506f8db79, 8957450e5744d59e, a803b4966933291a, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, b1327bdaf1fdb10d, 20cd66043e9dab55, f42a28fa00ccf0ea]
updated: 2026-07-02
covers_evidence: [432c23c0dd1c00f1, f07b6a3f3f344020, 55809dc9368e7936, 8f76e67ad854a6c0, 64ad8e685ed41a9b, 3abcf8c08cb66506, e214c4d6ded906fa, 4500a2b43ff7ed73, ebc3627096b332c8, 45c05959600cf833, 72d3e39506f8db79, 8957450e5744d59e, a803b4966933291a, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, b1327bdaf1fdb10d, 20cd66043e9dab55, f42a28fa00ccf0ea]
---

## TL;DR
Pin down a fixed set of tasks with known good outcomes and run agents against
them repeatedly. Unlike model benchmarks, agent benchmarks have to exercise
*tool use and multi-step trajectories* — booking, querying, fixing, coordinating
— so they double as integration tests for the whole agent, not just the model.

## State of the art
**Benchmark what the agent did**, not just its answer: rubric-style suites
score whether the right tools were called and the task was actually completed,
and structural benchmarks probe specific failure axes (e.g. DPBench on the
determinants of multi-agent coordination).

**Measure capability on your own tooling and out of distribution**: Hugging
Face's "is it agentic enough" workbench benchmarks open models against the
caller's actual tools, and "Running the Gauntlet" shows agents that top
familiar leaderboards degrade sharply in unfamiliar environments — so a high
public score is weak evidence for your workload. Reusable eval workbenches
(olmo-eval) package this into the model/agent development loop so
benchmarking is a standing harness, not a one-off.

**The harness is part of what you benchmark**: a cross-harness study reports
a deliberately simple agent loop reaching SOTA across 21 models on SWE-pro and
Terminal-Bench-style suites, evidence that elaborate scaffolding often adds
cost and variance without adding capability — so the benchmark should hold
the harness fixed and let it earn its complexity. Vendors are running this
in-house: GitHub's evaluation of its Copilot agentic harness across 20+ models
and many tasks scores results *and* token efficiency together, treating the
scaffold as a benchmark variable and elevating cost-per-solved-task to a
first-class metric alongside accuracy.

**Mined from real sessions**: rather than synthetic tasks, the newest suites
are mined from real sessions — EnterpriseClawBench builds enterprise-agent
tasks from actual workplace sessions where an agent reads heterogeneous
files, calls tools, and has to deliver a business artifact, so the benchmark
inherits the messiness of production instead of approximating it.

**Reproducibility** is the flip side of trusting a benchmark: because agent
runs touch the network, filesystem, and shifting tool versions, a score only
means something if the environment is fixed — Proctor packages coding-agent
benchmarks as signed, isolated bundles so a run can be reproduced (and a
leaderboard claim audited) rather than taken on faith.

**Adversarial tool environments**: rather than assuming tools behave, "Beyond
Function Calling" scores agents when tools time out, error, or return
malformed results, exposing agents that pass clean tool suites but cannot
recover when the environment misbehaves — the benchmark targets the *failure
recovery* path, not the happy path.

**Held-out, hard-to-memorize tasks**: practitioners are reaching for novel
environments a model can't have trained on (a Sherlock Holmes deduction board
game run as an LLM-agent eval) precisely because familiar leaderboards leak
into training. Both this and the adversarial-tool-environment axis answer a
gap practitioners keep voicing — public threads asking "what benchmarks
actually compare agent *harnesses*" (beyond Terminal-Bench) — that the
standard model leaderboards don't fill.

**Subsystem-specific benchmarks** isolate one capability instead of scoring
end-to-end task success: a suite for the failure modes of agent memory
(forgetting, stale recall, poisoned entries) and OpenRCA 2.0's shift from
outcome labels to causal process supervision for root-cause analysis both
grade an inner subsystem — the memory layer, the reasoning trajectory — so a
regression can be localized to the part that broke rather than inferred from
a fallen aggregate score. A microservice-failure-diagnosis benchmark
(AgentOps) extends the same process-over-outcome grading to ops agents,
scoring the diagnosis path over multimodal trace data and pulling
benchmarking toward [observability](/topic/agent-observability). The
subsystem list now has a fourth entry: MemSyco-Bench isolates whether
retrieved memories bias the agent toward sycophantic agreement rather than
a correct answer, a failure mode distinct from forgetting or poisoning (see
[agent memory](/topic/agent-memory)).

**Constructing and trusting the benchmark itself** is now its own line of
work, not a solved prerequisite: Reap automates curating coding-agent
benchmark tasks instead of hand-authoring them, addressing the same upkeep
cost that makes fixed suites expensive to maintain over time. A validity
critique of repository-level performance-optimization benchmarks (GSO,
SWE-Perf, SWE-fficiency) questions whether runtime-comparison suites
actually measure coding-agent capability or are instead artifacts of the
patch-application harness — the same "is the harness what you're measuring"
skepticism already raised for tool-reliability suites, now applied to
performance benchmarks.

Eval **transparency** is improving too, on the meta side: Hugging Face now
surfaces community "Every Eval Ever" results directly on model pages, making
the spread of scores visible rather than relying on a single headline number.

The **domain-specific and long-horizon** fronts are both advancing: ScarfBench
narrows to a single high-stakes enterprise task (migrating Java frameworks)
rather than a generic coding benchmark, following the "mined from real work"
pattern EnterpriseClawBench set; and Emergence World is built specifically to
grade long-horizon autonomy — sustained multi-step operation rather than a
single bounded task — the harder distribution-shift edge the "familiar
leaderboards degrade out of distribution" finding already flags.

## What's new
Benchmark **construction and trust** are getting scrutinized as their own
problem: Reap automates curating coding-agent benchmark tasks instead of
hand-authoring them, while a validity critique of repository-level
performance-optimization suites (GSO, SWE-Perf, SWE-fficiency) questions
whether they measure real coding-agent capability or artifacts of the
patch-harness. The subsystem-specific axis gains a fourth failure mode too
— MemSyco-Bench targets memory-induced sycophancy (see
[agent memory](/topic/agent-memory)).

**Subsystem-specific** grading is on the rise — isolating one capability
rather than scoring a whole task: a new suite targets the failure modes of
agent memory (forgetting, stale recall, poisoning) and OpenRCA 2.0 grades
root-cause analysis with causal process supervision (labels on the reasoning
steps, not just the outcome), so a regression localizes to the memory layer
or the trajectory instead of a fallen aggregate.

This complements a push toward **failure paths and held-out tasks** that
public leaderboards miss: "Beyond Function Calling" scores agents under
unreliable tool environments (time-outs, errors, malformed results) to test
recovery rather than the happy path, and practitioners are reaching for
novel, hard-to-memorize environments (a Sherlock Holmes deduction game as an
agent eval) because familiar suites leak into training — answering the
recurring "what benchmarks actually compare agent *harnesses*" gap.

Vendors now run **harness benchmarking in-house**: GitHub scores its Copilot
agentic harness across 20+ models on results *and* token efficiency, the
process-over-outcome grading reaches ops agents (a microservice-failure-
diagnosis AgentOps benchmark), and eval results are getting more transparent
(Hugging Face's "Every Eval Ever" on model pages).

This builds on suites mined from **real sessions** (EnterpriseClawBench) and
**reproducible packaging** (Proctor's signed, isolated bundles), all
reinforcing that public scores over-state real-workload performance and that
the harness itself is a benchmark variable.

Two more entries push the frontier further: **ScarfBench** narrows to a
single enterprise domain (Java framework migration) instead of generic
coding, and **Emergence World** targets long-horizon autonomy specifically,
grading sustained multi-step operation rather than one bounded task.

## Trade-offs
A fixed benchmark is reproducible and cheap to re-run, but it's a static
target: agents over-fit to it, it goes stale as tools change, and "passing"
can mean "memorized the distribution."

Building a benchmark on your own tooling is more predictive but is real work
to author and maintain, and small task sets have high variance.

Best as a regression gate (catch known failures) — complement with
[LLM-as-judge](/topic/llm-as-judge) on live traces for the open-ended cases a
fixed suite can't enumerate.

## Why it matters for platform engineers
Agent benchmarks are the CI gate of the agent stack: a fixed suite you run on
every prompt, model, or tool change to catch regressions before users do.

The leverage is building it from *your* environment and tools, because public
leaderboards systematically over-state how an agent will do on your workload
— and budgeting the upkeep, since a benchmark is only useful while it still
resembles production.
