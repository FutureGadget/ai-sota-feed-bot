---
slug: agent-evaluation
kind: obstacle
title: "Measuring whether an agent actually worked is hard"
area: evaluation
status: active
solutions: [llm-as-judge, agent-benchmarks]
obstacles: []
related_storylines: []
evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575, c579e90dd1110817, 27f5cba0a6308a00, 00678eb9b30563c3, 7ef376842f782ecd, 8957450e5744d59e, 979d921c237f1c0b, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, cf0a37dd32efaf51, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, 5d87a279aac331cb, 20cd66043e9dab55, 1bfbb319ced0695a, 20ef04d4cce6eb8c, d8ea565801623af0, 4a0a79e7203bae64, 37ded4dcb25847bf, ad296ea32f314908, c9f72591463a51bb, e9167e656930e3f1, 05a8c95d74885091, 2fce98e1c0265225]
updated: 2026-07-13
covers_evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575, c579e90dd1110817, 27f5cba0a6308a00, 00678eb9b30563c3, 7ef376842f782ecd, 8957450e5744d59e, 979d921c237f1c0b, 2e0b2f76a5b7e197, 274255c89788d5c4, 326b5d51b877e9cf, cf0a37dd32efaf51, 59e3931d5ce8feeb, d2b47e5ca2b10e4d, 5d87a279aac331cb, 20cd66043e9dab55, 1bfbb319ced0695a, 20ef04d4cce6eb8c, d8ea565801623af0, 4a0a79e7203bae64, 37ded4dcb25847bf, ad296ea32f314908, c9f72591463a51bb, e9167e656930e3f1, 05a8c95d74885091, 2fce98e1c0265225]
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

The eval-improvement loop is also being reframed as a **data-mining problem**
rather than a labeling exercise: LangChain's practice is to mine production
agent traces for failure clusters first, then fine-tune a judge on those
clusters (cheaper than a frontier judge) and use it to hill-climb agent
performance — treating "what should we eval" as a question the traces
themselves answer, not a rubric written up front.

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

A **direct human-vs-automated comparison** sharpens the same warning with a
controlled test instead of a war story: Hamel Husain checked 100
human-annotated traces against automated eval systems and found real
divergence between what the automated pipeline scored and what a human
rater would — evidence you cannot certify an automated eval suite by
inspecting a handful of cases, you have to measure its agreement with human
judgment directly. Practitioner tooling is starting to build that check
into the workflow itself rather than leaving it as a one-off audit: an
open-source agent-output evaluator runs human labels and LLM judges over the
same traces side by side instead of treating human review as a fallback
when the automated judge is in doubt.

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

A fourth front pushes back on **LLM-as-judge itself**: rather than fine-tuning
or auditing the judge, a deterministic-replacement approach for stateful agent
evaluation skips model-graded scoring altogether for the class of tasks where
state transitions can be checked directly — a reminder that "judge with
another LLM" is a default, not the only option, when the task admits a
programmatic check. A parallel critique targets the **benchmarks** rather
than the judge: performance-optimization suites (GSO, SWE-Perf, SWE-fficiency)
that score coding agents by comparing runtime against baselines turn out to
have their own reliability problems as measurement instruments, sharpening
the standing "familiar benchmarks over-state capability" finding into "the
benchmark's own numbers can be noisy," not just non-representative. A
practitioner analysis puts a number on that noise: one standard deviation
between repeated runs of the *same* model on a coding task measured 7.5% —
bigger than the gap between the best- and worst-ranked models in the
comparison — and dropping or swapping a handful of tasks from a ~100-task
set was enough to flip which model wins, the benchmark equivalent of a race
course shaping who looks like the best cyclist. Consolidation is showing up
on the tooling side too: Harbor pairs LangSmith's sandboxes and observability
with Deep Agents into one stack specifically for evaluating long-running,
stateful agents, and practitioner write-ups (Pendo tracing its Novus product
agent from user behavior to code fixes with LangSmith) show eval, tracing,
and monitoring converging into one workflow rather than three separate
tools.

A fifth front lands on **testing methodology**, not just labels: LLM-written
fuzzers surface real, serious bugs within minutes but have coverage gaps a
hastily hand-written fuzzer would catch, so raw bug-finding recall isn't
proof of thorough testing. The practical fix for the false positives that
follow is ensembling reviewers — independent agents checking the same
artifact (a video, a generated test) under different personas, including a
deliberately contrarian one, which cuts false positives more reliably than
swapping in a stronger single model. Both findings converge on the same
conclusion: a reasonable process around the model is at least as load-bearing
as which model you use.

A sixth front turns the "how hard is this case" question itself into a
measurable dial. Discovery Bench uses **surprisal** — the residual
uncertainty a query leaves about the correct answer — to generate the same
evaluation case at calibrated ambiguity levels instead of hand-labeling
cases "easy" or "hard." Run against a real agent, the technique exposes a
**cliff effect** invisible to a single pass/fail run: F1 dropped from 1.00 at
neutral phrasing to 0.00 at high ambiguity on the identical query, agent, and
ground truth, and mid-ambiguity cases sometimes outperformed low-ambiguity
ones — revealing implementation quirks (over-retrieval of time-sharded
tables, context blow-up) a scalar pass rate would hide. The same audit found
the benchmarks' own ground truth wrong on a meaningful slice of cases
(6.49% of MMLU), reinforcing that the eval data needs evaluating too, not
just the agent. And a widely-used coding benchmark got the same scrutiny:
OpenAI's own analysis raises reliability and accuracy concerns in SWE-Bench
Pro specifically, adding a second named benchmark (alongside GSO, SWE-Perf,
SWE-fficiency above) to the "the benchmark's own numbers can be noisy" list.
Benchmark **coverage** is widening too: Agents' Last Exam, co-led with UC
Berkeley and 300+ domain experts, targets long-horizon, economically
valuable professional tasks with verifiable outcomes across 55 sub-industries
— a deliberate move past narrow coding/tool-use suites toward the kind of
real-world work static leaderboards have historically under-represented.

Real-world deployment write-ups are converging on the same **eval, tracing,
and monitoring as one workflow** conclusion practitioner reports flagged
earlier: Schneider Electric runs one LangSmith workspace per AI product
(not per environment) so production traces flow straight back into
development datasets, lets domain experts annotate real usage without
developer-level tooling access, and gates promotion on a maturity framework
tracking instrumentation, offline eval coverage, online evaluators, and user
feedback — evaluation as a lifecycle gate across 60+ products, not a
pre-launch checkbox.

## What's new
A controlled test puts a number on the "trust but verify the eval" lesson:
checking 100 human-annotated traces against automated eval systems found
real divergence between the two, and practitioner tooling is starting to
run human labels and LLM judges side by side over the same traces rather
than treating human review as a fallback for a doubted automated verdict.

## Why it matters for platform engineers
Eval is the regression test of the agent stack — without it you cannot tell
a prompt tweak or model upgrade from a silent regression, and you cannot put
a number on reliability.

But running a frontier LLM as a judge over every production trace is its own
cost-and-latency line item, and a benchmark your agent has effectively
trained on gives false confidence. The practical job is building a cheap,
trustworthy, trajectory-aware eval harness you can run in CI and on live
traffic — closer to observability than to a one-time accuracy check.
