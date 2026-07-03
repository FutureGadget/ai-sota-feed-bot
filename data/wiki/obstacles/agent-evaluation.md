---
slug: agent-evaluation
kind: obstacle
title: "Measuring whether an agent actually worked is hard"
area: evaluation
status: active
solutions: [llm-as-judge, agent-benchmarks]
obstacles: []
related_storylines: [deep-research]
evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575, c579e90dd1110817, 27f5cba0a6308a00, 00678eb9b30563c3, 7ef376842f782ecd, 8957450e5744d59e, 979d921c237f1c0b, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, cf0a37dd32efaf51, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, 9bf2f6419fda7872, 1bfbb319ced0695a]
updated: 2026-07-02
covers_evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575, c579e90dd1110817, 27f5cba0a6308a00, 00678eb9b30563c3, 7ef376842f782ecd, 8957450e5744d59e, 979d921c237f1c0b, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, cf0a37dd32efaf51, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, 9bf2f6419fda7872, 1bfbb319ced0695a]
---

## TL;DR
A chatbot is graded on its final answer; an agent has to be graded on what it
*did* — the multi-step trajectory of tool calls, retries, and decisions that
led there. Outputs are non-deterministic, "correct-looking" answers can come
from broken paths, and a benchmark the agent has effectively memorized tells
you nothing about a new environment. Knowing whether an agent works in
production is itself an unsolved engineering problem.

## State of the art
Evaluation is splitting into two complementary jobs: judging the steps, and
judging results under real-world conditions.

**Trajectory / process evaluation** judges the steps, not just the final
string: did the agent call the right tools, recover from errors, and avoid
loops. Tooling like rubric-style checks ("test what your LLM agent *did*, not
just what it said") and failure-detection systems that emit categorized
failures with causal chains (AWS's Strands Evals) reflect this shift toward
structured, step-level verdicts. The labels themselves are moving the same
way: OpenRCA 2.0 reframes root-cause analysis — a holistic test of
long-context, multi-step reasoning, and tool use — from outcome labels to
causal process supervision, scoring whether the agent reasoned through the
right intermediate steps rather than only whether it landed the final
answer, which is what trajectory-aware grading needs to train and audit a
judge against.

**Outcome evaluation under distribution shift** is the second job: a
recurring finding is that agents look strong on familiar benchmarks and
degrade sharply when "run beyond familiar environments," so static
leaderboards over-state real-world capability. Because human grading doesn't
scale to long traces, the field leans on **LLM-as-judge** scoring (now being
cost-reduced by fine-tuning small judges on production traces, and pushed
further by shared-backbone multi-head classifiers — Morph Reflexes reads a
trace once and scores several behavioral failure modes off the same forward
pass for sub-30ms latency) and on **agent benchmarks** that exercise an agent
against its own tooling — including domain-narrow suites (ScarfBench, on
enterprise Java migration) and long-horizon autonomy labs (Emergence World)
that push past single bounded tasks. The frontier edge is *pre*-deployment
prediction — simulating deployment on real conversation data to forecast
behavior before release rather than measuring it after an incident.

Two countercurrents now temper the optimism. The **judge itself is under
audit**: BabelJudge measures LLM-as-judge reliability across languages *and*
agent trajectories and finds the systematic biases (position, verbosity,
language) that raw accuracy hides — so a trajectory judge needs its own
validation before you trust its verdicts.

Hard-won **practitioner write-ups** (three years of evals for financial
agents; a post-mortem on why most evals would miss a real Linear sales-email
failure) converge on the same warning: an eval suite passes while the agent
fails the way that actually matters, because the suite never encoded the
real-world failure.

The constructive counter-reframe lands from the same camp: "*it's hard to
eval*" is a **product smell**, not an excuse — if you can't specify what good
output is, that is a fuzzy-spec problem to fix, and the discipline of writing
the eval forces the product clarity, rather than the difficulty proving eval
impossible.

The unit under test is also widening from a single agent to the whole
**harness**: GitHub's evaluation of its Copilot agentic harness across 20+
models and many tasks grades the harness's results *and* token efficiency
together, treating the agent+model+scaffold as the thing you benchmark and
making cost-per-solved-task a first-class eval metric. And eval is
converging with [observability](/topic/agent-observability): a multi-dataset
benchmark for LLM agents in microservice failure diagnosis (AgentOps) scores
process over outcome on multimodal trace data — grading the diagnosis path,
not just the verdict — so the trace becomes the shared substrate for both.

A third front opens on the *output* of coding agents specifically: as agents
write more of the code, "tests passing" stops being sufficient evidence to
merge, because a green suite says nothing about the structural quality or
robustness of what was generated — and the human cost of reviewing it is
becoming the new bottleneck. Topos attacks this with **structural
code-quality metrics for agent-written programs** — graded signals on the
code itself rather than a pass/fail test gate — reframing eval for code
agents as "is this change good," not just "does it run."

Two independent entrants target the eval *process* itself rather than the
scoring logic: QUALITY.md is one developer's open specification, agent
skill, and CLI for a holistic quality-evaluation process a team can adopt
directly, framed explicitly for "loop engineering." Separately, on the
runner side, long-running stateful agents are outgrowing single-shot test
harnesses — Harbor packages Deep Agents, LangSmith sandboxes, and
observability into a unified stack built specifically to evaluate agents
that don't terminate in one call, tying evaluation to
[observability](/topic/agent-observability) at the runner level, not just
the trace-analysis level.

## What's new
Two new process-level entrants: QUALITY.md, one developer's open spec/CLI
for a holistic quality-evaluation process, and Harbor, which gives
long-running, stateful agents (Deep Agents workloads) a purpose-built
runner that plugs in LangSmith sandboxes and observability rather than
reusing single-shot test harnesses.

**Process-level grading** is getting first-class labels: OpenRCA 2.0 moves
root-cause-analysis evaluation from outcome labels to causal process
supervision, scoring the intermediate reasoning steps rather than just the
final verdict — the dataset side of the shift to trajectory-aware eval.

Scrutiny has also turned on the **eval machinery itself**: BabelJudge shows
trajectory judges carry measurable position/language bias under the hood,
and practitioner post-mortems (financial-agent evals, the missed Linear
failure) argue that a green eval suite routinely hides the failure that
matters — so "build a judge" is giving way to "validate the judge and the
suite against real failures."

A new angle targets **coding agents' output**: with agents writing more
code, "tests passing" no longer proves the change is good, so Topos scores
the structural quality of agent-written programs directly, treating
review-grade signal as the eval rather than a pass/fail gate.

Two reframes land this round: the constructive "*it's hard to eval is a
product smell*" argument (inability to eval signals a fuzzy spec to fix, not
an impossible task), and the **unit of eval widening to the whole harness**
— GitHub benchmarks its Copilot agentic harness across 20+ models scoring
results and token efficiency, while a microservice-failure-diagnosis
benchmark (AgentOps) grades the diagnosis process on trace data, pulling
eval and [observability](/topic/agent-observability) onto the same
substrate.

Eval **transparency** is moving too: Hugging Face now surfaces community
"Every Eval Ever" results on model pages.

The **cheap-judge cost lever** gets sharper too: Morph Reflexes shares one
backbone's compute across many trace-classifier heads instead of running a
separate small model per behavioral signal, and two new benchmarks push the
domain axis (ScarfBench's enterprise Java-migration task) and the horizon
axis (Emergence World's long-horizon autonomy lab) further than existing
suites reach.

This sits alongside the earlier shift to graded process — trace judges that
score trajectories at ~1/100th frontier cost and root-cause failure
detectors — and mounting evidence that familiar-benchmark scores collapse
out of distribution.

## Why it matters for platform engineers
Eval is the regression test of the agent stack — without it you cannot tell
a prompt tweak or model upgrade from a silent regression, and you cannot put
a number on reliability.

But running a frontier LLM as a judge over every production trace is its own
cost-and-latency line item, and a benchmark your agent has effectively
trained on gives false confidence. The practical job is building a cheap,
trustworthy, trajectory-aware eval harness you can run in CI and on live
traffic — closer to observability than to a one-time accuracy check.
