---
slug: agent-evaluation
kind: obstacle
title: "Measuring whether an agent actually worked is hard"
area: evaluation
status: active
solutions: [llm-as-judge, agent-benchmarks]
obstacles: []
related_storylines: [deep-research]
evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575, c579e90dd1110817, 27f5cba0a6308a00, 00678eb9b30563c3, 7ef376842f782ecd]
updated: 2026-06-26
covers_evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575, c579e90dd1110817, 27f5cba0a6308a00, 00678eb9b30563c3, 7ef376842f782ecd]
---

## TL;DR
A chatbot is graded on its final answer; an agent has to be graded on what it
*did* — the multi-step trajectory of tool calls, retries, and decisions that
led there. Outputs are non-deterministic, "correct-looking" answers can come
from broken paths, and a benchmark the agent has effectively memorized tells
you nothing about a new environment. Knowing whether an agent works in
production is itself an unsolved engineering problem.

## State of the art
Evaluation is splitting into two complementary jobs. The first is **trajectory /
process evaluation** — judging the steps, not just the final string: did the
agent call the right tools, recover from errors, and avoid loops. Tooling like
rubric-style checks ("test what your LLM agent *did*, not just what it said")
and failure-detection systems that emit categorized failures with causal chains
(AWS's Strands Evals) reflect this shift toward structured, step-level verdicts.
The second is **outcome evaluation under distribution shift**: a recurring
finding is that agents look strong on familiar benchmarks and degrade sharply
when "run beyond familiar environments," so static leaderboards over-state
real-world capability. Because human grading doesn't scale to long traces, the
field leans on **LLM-as-judge** scoring (now being cost-reduced by fine-tuning
small judges on production traces) and on **agent benchmarks** that exercise an
agent against its own tooling. The frontier edge is *pre*-deployment prediction —
simulating deployment on real conversation data to forecast behavior before
release rather than measuring it after an incident. Two countercurrents now
temper the optimism. First, the judge itself is under audit: BabelJudge measures
LLM-as-judge reliability across languages *and* agent trajectories and finds the
systematic biases (position, verbosity, language) that raw accuracy hides — so a
trajectory judge needs its own validation before you trust its verdicts. Second,
hard-won practitioner write-ups (three years of evals for financial agents; a
post-mortem on why most evals would miss a real Linear sales-email failure)
converge on the same warning: an eval suite passes while the agent fails the way
that actually matters, because the suite never encoded the real-world failure.
A third front opens on the *output* of coding agents specifically: as agents
write more of the code, "tests passing" stops being sufficient evidence to merge,
because a green suite says nothing about the structural quality or robustness of
what was generated — and the human cost of reviewing it is becoming the new
bottleneck. Topos attacks this with **structural code-quality metrics for
agent-written programs** — graded signals on the code itself rather than a
pass/fail test gate — reframing eval for code agents as "is this change good,"
not just "does it run."

## What's new
Scrutiny has turned on the eval machinery itself: BabelJudge shows trajectory
judges carry measurable position/language bias under the hood, and practitioner
post-mortems (financial-agent evals, the missed Linear failure) argue that a
green eval suite routinely hides the failure that matters — so "build a judge"
is giving way to "validate the judge and the suite against real failures." A new
angle targets coding agents' *output*: with agents writing more code, "tests
passing" no longer proves the change is good, so Topos scores the **structural
quality of agent-written programs** directly, treating review-grade signal as the
eval rather than a pass/fail gate. This sits alongside the earlier shift to
graded *process* — trace judges that score trajectories at ~1/100th frontier cost
and root-cause failure detectors — and mounting evidence that familiar-benchmark
scores collapse out of distribution.

## Why it matters for platform engineers
Eval is the regression test of the agent stack — without it you cannot tell a
prompt tweak or model upgrade from a silent regression, and you cannot put a
number on reliability. But running a frontier LLM as a judge over every
production trace is its own cost-and-latency line item, and a benchmark your
agent has effectively trained on gives false confidence. The practical job is
building a cheap, trustworthy, trajectory-aware eval harness you can run in CI
and on live traffic — closer to observability than to a one-time accuracy check.
