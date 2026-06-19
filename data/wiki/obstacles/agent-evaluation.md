---
slug: agent-evaluation
kind: obstacle
title: "Measuring whether an agent actually worked is hard"
area: evaluation
status: active
solutions: [llm-as-judge, agent-benchmarks]
obstacles: []
related_storylines: [deep-research]
evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575]
updated: 2026-06-19
covers_evidence: [b8b632a161a052e9, 12500c0bbe5e4d6f, 4235792e910ea51a, 55809dc9368e7936, f07b6a3f3f344020, c000018ba1f03575]
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
release rather than measuring it after an incident.

## What's new
The conversation has moved past "did it answer correctly" to graded *process*:
trace judges that score trajectories (LangChain/Fireworks report matching
frontier-judge quality at ~1/100th the cost by fine-tuning an open model on
production traces) and root-cause failure detectors, plus mounting evidence that
familiar-benchmark scores collapse out of distribution.

## Why it matters for platform engineers
Eval is the regression test of the agent stack — without it you cannot tell a
prompt tweak or model upgrade from a silent regression, and you cannot put a
number on reliability. But running a frontier LLM as a judge over every
production trace is its own cost-and-latency line item, and a benchmark your
agent has effectively trained on gives false confidence. The practical job is
building a cheap, trustworthy, trajectory-aware eval harness you can run in CI
and on live traffic — closer to observability than to a one-time accuracy check.
