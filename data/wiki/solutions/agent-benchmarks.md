---
slug: agent-benchmarks
kind: solution
title: "Agent benchmarks: fixed tasks that exercise real tool use"
status: active
obstacles: [agent-evaluation]
related_storylines: []
evidence: [432c23c0dd1c00f1, f07b6a3f3f344020, 55809dc9368e7936, 8f76e67ad854a6c0, 64ad8e685ed41a9b, 3abcf8c08cb66506, e214c4d6ded906fa, 4500a2b43ff7ed73, ebc3627096b332c8, 45c05959600cf833, 72d3e39506f8db79, 8957450e5744d59e, a803b4966933291a, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, b1327bdaf1fdb10d, bb53999f247d993c, 33347a0b1de54b78, 76abb26fe81fb012, d8ea565801623af0, 64cfadf91532a8d8, aebd52611d2bd6be, 7a6b5f1921def089, 4c751bb0914d78b0, 13619e816aa57836, 6db5a9df32bfdf66, 44f0a4a9788e78b0, 1b0f607e0ee0acbd, 47fb1c35deeeb68f, ddce7e0a20f47f4f]
updated: 2026-07-27
covers_evidence: [432c23c0dd1c00f1, f07b6a3f3f344020, 55809dc9368e7936, 8f76e67ad854a6c0, 64ad8e685ed41a9b, 3abcf8c08cb66506, e214c4d6ded906fa, 4500a2b43ff7ed73, ebc3627096b332c8, 45c05959600cf833, 72d3e39506f8db79, 8957450e5744d59e, a803b4966933291a, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, b1327bdaf1fdb10d, bb53999f247d993c, 33347a0b1de54b78, 76abb26fe81fb012, d8ea565801623af0, 64cfadf91532a8d8, aebd52611d2bd6be, 7a6b5f1921def089, 4c751bb0914d78b0, 13619e816aa57836, 6db5a9df32bfdf66, 44f0a4a9788e78b0, 1b0f607e0ee0acbd, 47fb1c35deeeb68f, ddce7e0a20f47f4f]
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

**Value-poisoning** is a related but distinct adversarial axis: rather than
malformed tool results, ActionRail's benchmark tests whether an agent
executes corrupted-but-plausible business data — an altered payment account,
a fake refund address — buried inside an otherwise legitimate document.
Across 8 models and 4 providers on 10 consequential workflows, cost-optimized
models failed 48.3-63.3% of the time versus 1.7-21.7% for frontier models,
and a guard layer blocked all 480 protected attack cases with zero false
positives on legitimate ones — evidence that this failure mode needs a
dedicated defense, not just a stronger model.

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
benchmarking toward [observability](/topic/agent-observability).

Eval **transparency** is improving too, on the meta side: Hugging Face now
surfaces community "Every Eval Ever" results directly on model pages, making
the spread of scores visible rather than relying on a single headline number.

**Whole-agent breadth and harness-level replay** are a newer axis alongside
the domain-narrow and long-horizon ones below: OmniaBench derives an
application-oriented taxonomy from app stores, product docs, and web
retrieval to span 1,431 tasks across 90 top-level domains with explicit
state spaces, exposing headroom (even frontier models clear only about half
the suite) that narrower coding/tool-use benchmarks don't surface. On the
harness side, Favur Evals scores a 14-agent multi-model harness on eight
composite engineering subjects computed from each run's own artifacts (lint,
test results, tool telemetry) and pairs every score with a full deterministic
replay of that run — turning the reproducibility this page argues for into a
feature of the benchmark itself, not just a property to demand of one.

The **domain-specific and long-horizon** fronts are both advancing: ScarfBench
narrows to a single high-stakes enterprise task (migrating Java frameworks)
rather than a generic coding benchmark, following the "mined from real work"
pattern EnterpriseClawBench set; and Emergence World is built specifically to
grade long-horizon autonomy — sustained multi-step operation rather than a
single bounded task — the harder distribution-shift edge the "familiar
leaderboards degrade out of distribution" finding already flags.

**Benchmark upkeep is being automated**, addressing the standing trade-off
that a hand-built benchmark is real work to author and maintain: Reap
automates curation of coding-agent benchmark tasks rather than requiring a
team to hand-pick and refresh them. A new **environment-readiness** angle
also appears: AeroScore scores how well existing documentation portals
support AI agents in the first place, evaluating the environment an agent
has to operate in rather than the agent itself — a precondition check that
sits upstream of any task benchmark. On the subsystem-specific front,
TestEvo-Bench adds an executable, live benchmark for test-and-code
co-evolution, isolating whether an agent keeps tests in sync with the code
it changes. And a new capability frontier opens on program understanding:
MirrorCode benchmarks agents rebuilding entire programs from behavior alone
(black-box reconstruction), pushing past "modify existing code" into
"reconstruct it from how it behaves." The domain-narrow list keeps growing:
GameEngineBench scores coding agents against real C++ game-engine runtime
environments, extending "mined from real work, one domain at a time"
(alongside ScarfBench's Java migrations) into a runtime with real-time
simulation, physics, and rendering constraints a generic coding benchmark
doesn't exercise.

The domain-narrow list keeps widening past coding into **cross-system
integration**: Stripe's 11-environment benchmark scores agents on checkout
migration, billing API work, and full-stack browser checkout, with the best
runs needing roughly 63 interaction turns — a numbered, named-vendor
addition alongside ScarfBench and GameEngineBench, and one where the two
leading models (92% vs. 73%) failed the identical validation step rather
than differing on raw coding capability. The scientific-computing edge of
the domain-narrow trend also gets a benchmark: Imaging-101 scores coding
agents on 57 expert-verified computational-imaging tasks across six
scientific domains and three tracks (planning, unit tests, end-to-end
reconstruction), finding failures specific to the domain (physical-convention
handling, pipeline integration) beyond generic coding skill.

**Harness-vs-harness comparison** gets its own named entrant: OpenBench
scores different coding-agent harnesses against each other on the same
tasks, answering the standing practitioner question this page already
flags ("what benchmarks actually compare agent harnesses, beyond
Terminal-Bench") with a dedicated suite rather than repurposing a
model-comparison benchmark.

**Language and domain granularity** is a newer axis alongside the
domain-narrow and subsystem-specific ones above: HalluTruthQA benchmarks
hallucination detection, span-level localization, factual verification, and
explanation quality in Arabic question answering across four
knowledge-intensive domains (Islamic knowledge, history, science,
geography), with 2,400 expert-curated examples pairing each answer with a
verified reference, six verification candidates, and — for hallucinated
answers — character-level erroneous spans and human-written explanations.
Evaluated zero-shot against 4 open-source LLMs, no model tops every
sub-task, evidence the benchmark landscape is starting to move past
English-centric, response-level hallucination labels into non-English,
finer-grained grading.

**Physical-world action** opens as a domain frontier alongside the
domain-narrow suites above: Anthropic and Andon Labs built Drone-Bench to
test whether a model can autonomously fly a drone to locate and follow a
person, extending "exercise real tool use" past software environments into
embodied control — a harder distribution shift than a new coding domain,
since the tool being called is a physical actuator with real-world latency
and failure modes rather than an API.

A **construct-validity critique** now questions what a benchmark score
actually measures, not just how reproducible or adversarial-resistant it is:
a protocol-validity analysis argues many agent benchmarks conflate genuine
task difficulty with scaffolding and protocol artifacts, so two agents can
score differently because of how their harness happens to interact with the
benchmark's protocol, not because one is more capable — sharpening this
page's standing "the harness is part of what you benchmark" finding into a
challenge to the benchmark's own validity as a measurement instrument, not
just its reproducibility or noise.

## What's new
A construct-validity critique argues many agent benchmarks conflate genuine
task difficulty with scaffolding/protocol artifacts, meaning a score gain can
reflect a better-fitted harness rather than a more capable agent — the same
"harness is part of what you benchmark" thread this page already tracks,
now framed as a validity problem with the benchmark itself rather than only
its reproducibility or noise.

## Trade-offs
A fixed benchmark is reproducible and cheap to re-run, but it's a static
target: agents over-fit to it, it goes stale as tools change, and "passing"
can mean "memorized the distribution."

Building a benchmark on your own tooling is more predictive but is real work
to author and maintain, and small task sets have high variance — measured,
not just suspected: one practitioner found a model's own run-to-run standard
deviation (7.5% on a coding task) exceeded the best-to-worst-model gap, and
swapping a few tasks out of a ~100-task set flipped which model ranked
first. Two models can also both look "cheaper" and "more expensive" than
each other depending on which tasks the comparison uses — so a single
leaderboard number is a claim about that task set, not a general fact about
the model.

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
