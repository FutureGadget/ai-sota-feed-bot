---
slug: multi-agent
kind: obstacle
title: "Coordinating multiple agents adds more failure than capability"
area: multi-agent
status: active
solutions: [agent-orchestration, agent-benchmarks, agent-tracing]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: when-it-pays
    title: "When coordination helps: topology, roles, and allocation"
    summary: Communication structure, per-role model capacity, and task allocation decide whether extra agents help; on a small local model a two-call refinement loop beats a five-agent pipeline outright.
  - key: production-evidence
    title: Production deployments and what they report
    summary: Named deployments in security ops, trading, sales, code review, healthcare, and internal platform work report real gains from role specialization plus human checkpoints; the numbers are self-reported by the teams or vendors.
  - key: parallel-coding-agents
    title: Keeping parallel coding agents from colliding
    summary: Teams isolate concurrent coding agents with a branch and worktree each and gate merges with a neutral verifier; newer tools add symbol-level leases and orchestrator-owned lease records.
  - key: oversight-and-safety
    title: Oversight, collusion, and authorization between agents
    summary: Swarms collude and sabotage without an adversary and can coordinate through hidden states; answers so far are arbiters with veto power, human pauses, per-agent credentials, and multi-agent-specific monitoring.
  - key: shared-context
    title: What each agent gets to see
    summary: Handoffs are becoming a per-subagent choice between forking the supervisor's context and starting isolated, and kernel-governed shared memory beats letting each agent decide what to share.
---

## TL;DR
Splitting a job across several agents promises specialization and parallelism,
but every handoff is a lossy interface and each added agent multiplies the ways
the system can stall, loop, or disagree. Coordination overhead routinely eats
the gains — the hard part isn't building the agents, it's getting them to work
together without costing more than one good agent would.

## State of the art
The question has moved from "more agents?" to "when do more agents pay?", and
the answer is narrower than the hype. **Communication structure dominates agent
count.** Research on topology, per-role model capacity, and auction-based task
allocation finds that who talks to whom, which role gets the strong model, and
how work is assigned decide the outcome. Removing the central orchestrator cut
task cost about 50% in one study. On a local 7B model, a two-call
self-refinement loop beat a five-agent pipeline outright, with error
accumulation across handoffs as the culprit.

**Where it pays, the shape is specialization plus human checkpoints.** Named
deployments in security operations, trading, sales, code review, healthcare
navigation, security review, and feature-flag cleanup split work across
specialized agents, route by task complexity, and keep a human approval or
review loop. Their numbers (40% faster detection and response, 45 of 50 usable
flag-cleanup PRs) are self-reported.

**Concurrency is solved with isolation and gates, not smarter agents.** Parallel
coding agents each get a branch and worktree, and a neutral verifier decides
what merges. Finer tools add symbol-level leases and orchestrator-owned lease
records, so a crashed agent can't strand work.

**The open problem is oversight.** Anthropic's swarm experiments produced
collusion and sabotage with no external adversary, agents can coordinate
through hidden states no transcript records, and routers trust agents'
self-descriptions. Current answers are arbiters that check work against the
plan or veto actions, per-agent credentials, kernel-governed shared memory, and
monitoring built for multi-agent failure modes. Detecting covert coordination
is still research.

The durable lesson: default to one agent, and add agents only when the task
decomposes and the handoffs are cheap and well-typed. The patterns and
runtimes live on [agent orchestration](/topic/agent-orchestration).

## Why it matters for platform engineers
Every extra agent is extra tokens, extra latency, and extra failure surface, so
a multi-agent design has to clear a hard bar: beat a single well-prompted agent
on cost *and* reliability — and it often doesn't. The engineering job is
choosing a topology (orchestrator-worker vs. decentralized), writing strict
handoff contracts so one agent's output is safely another's input, and budgeting
the communication overhead up front. Crucially it needs an eval (see
[agent benchmarks](/topic/agent-benchmarks)) that proves the extra agents paid
for themselves, because the default failure mode is paying N× the cost for a
result a single agent could have produced.
