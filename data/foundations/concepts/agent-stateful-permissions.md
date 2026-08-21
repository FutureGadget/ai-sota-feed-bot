---
slug: agent-stateful-permissions
title: "Why can a permission check that's correct for a single tool call still let an agent break the rules across many?"
question: "Why can a permission check that's correct for a single tool call still let an agent break the rules across many?"
summary: "A tool-call policy that only evaluates the current request, in isolation, can be individually correct on every call and still let an agent violate an intended limit across a sequence — AWS's Dogwood shows a $5,000 transfer cap defeated by three concurrent $2,000 requests when the policy counts settled responses instead of requests in flight, and ships four operators for reading an agent's event history to close exactly that gap."
status: active
cluster: safety
updated: 2026-08-21
audience: "strong-software-engineer"
related_topics: [mcp, agent-sandboxing, tool-use]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: story-410ca031ddd240de-aws-dogwood
    kind: story
    sid: "410ca031ddd240de"
    title: "AWS Open-Sources Dogwood, Extending Cedar to Govern Sequences of Agent Tool Calls"
    note: "AWS open-sourced Dogwood (Apache 2.0), an extension to the Cedar policy language that adds a `when temporal` clause alongside Cedar's standard `when`, letting a policy read an agent's event history instead of evaluating only the current request. Four operators, defined as standard-library macros over Metric First-Order Temporal Logic, cover the common patterns: `formerly` (did X happen within a time window), `count_within` (how many times an action occurred), `count_distinct_within` (how many distinct values appeared), and `sum_within` (a running total). The announcement's own example: a $5,000 transfer cap written to sum settled response amounts can be defeated by three concurrent $2,000 transfers, because none of the three individual requests exceeds the cap and none has settled yet when the next one is evaluated — the fix is counting against requests as they're issued, not responses as they land. AWS is explicit that the reference interpreter is for exploring and testing the language, not production authorization, and that using temporal conditions gives up Cedar's normal automated formal-analysis guarantees."
  - id: story-e3560887ce822a61-cloudflare-writeguard
    kind: story
    sid: "e3560887ce822a61"
    title: "Cloudflare WriteGuard Brings Fine-Grained Security Controls for MCP Servers"
    note: "Cloudflare's WriteGuard (private beta, no production results reported yet) sits behind Cloudflare's MCP server portal as a shared policy and audit layer, intercepting MCP tool calls and evaluating them against tool-specific policies before allowing or blocking them. It assigns each operation a risk tier — read-only, minimal impact, contained write, or critical — so a merge-request completion or production deploy is gated differently than a read call, without requiring every individual MCP server to reimplement that tiering itself. Cloudflare's stated rationale: 'Reimplementing [controls] in each server would take more work and produce inconsistent behavior.'"
  - id: agent-stateful-permissions-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    note: "Dogwood and WriteGuard attack the same gap from different angles. Dogwood gives policy authors the vocabulary to express cross-call state directly in the policy language itself; WriteGuard centralizes per-operation risk tiering so many MCP servers share one enforcement point instead of each reimplementing it. Neither is a finished, battle-tested production control yet — Dogwood's reference interpreter is explicitly not for production use, and WriteGuard is in private beta with no measured results — but both are independent 2026 evidence that per-request authorization checks are no longer treated as sufficient for agents that act in sequences."
covers_evidence:
  - story-410ca031ddd240de-aws-dogwood
  - story-e3560887ce822a61-cloudflare-writeguard
  - agent-stateful-permissions-editorial-synthesis
---

## Builder consequence
If your agent's tool-call authorization checks each request in isolation — the classic RBAC pattern, and what Cedar evaluates by default — you can write a policy that is provably correct for every single call and still lets the agent do something the policy was meant to prevent. AWS's own example: a $5,000 transfer cap, checked correctly against every individual request, is defeated by issuing three concurrent $2,000 transfers, because no single request crosses the limit and the running total the policy checks hasn't caught up yet. The bug isn't in the cap logic; it's in evaluating a stateful rule with a stateless check.

## Short answer
A policy that needs to reason about what an agent has already done — approval-before-acting, rate limits, "stop after touching confidential data" — needs access to the agent's event history, not just the current request. AWS's Dogwood adds this to Cedar as a `when temporal` clause with four operators for history queries: `formerly` (did something happen in a window), `count_within` (how many times), `count_distinct_within` (how many distinct values), and `sum_within` (a running total). The operator choice matters less than what it counts: Dogwood's own example shows a rate limit defeated by counting *settled responses* instead of *requests in flight* — three concurrent requests each individually under the cap can still blow through it before any of them settles.

## Builder model
Split "does this tool call need authorization" into two different questions, because they need different mechanisms:

- **Is this one request allowed, on its own?** A stateless per-request check answers this — the caller, the resource, the action, evaluated fresh each time. This is what most authorization already does, and it's sufficient for most tool calls.
- **Is this request allowed given what the agent has already done?** This needs history: an approval workflow ("get a human sign-off before this class of action"), a rate or spend limit ("no more than N in a window"), or a sequencing rule ("don't contact an external party after this session touched confidential data"). A stateless check structurally cannot answer this — it has no memory of the prior calls.

The second category is where naive implementations break, and not just from missing history entirely. Even a check that does track history can fail if it counts the wrong event — Dogwood's transfer-cap example counts confirmed, settled transfers rather than transfers as they're requested, so several requests can be in flight and under the cap simultaneously before any of them lands and updates the running total.

## Mechanism
Cedar, the policy language Dogwood extends, evaluates a request against a policy set using only that request's own context — principal, action, resource, and any attributes attached to the call. This is deliberate: stateless evaluation is what lets Cedar formally verify properties of a policy set (no request can ever be both permitted and denied, for example) without simulating every possible sequence of calls.

Dogwood adds a second evaluation path alongside that stateless one. A `when temporal` clause is translated into ordinary Cedar context fields, populated from the agent's event history, before the stateless evaluator runs — so the temporal reasoning happens once, up front, and the rest of policy evaluation stays unchanged. The four operators cover the shapes that come up in practice: has this occurred recently (`formerly`), how many times has it occurred (`count_within`), how many distinct values have occurred (`count_distinct_within`), and what's the running sum (`sum_within`).

The concurrency trap in AWS's own example is the important detail: a policy written as `sum_within(response.amount, 1h) <= 5000` looks correct and passes every test that runs transfers one at a time. It fails under concurrency because three $2,000 requests can each be evaluated, and each individually pass, before any of their responses have settled and been summed — the running total the policy checks is still $0 when the third request is evaluated. Writing the same rule against *request* events instead of *response* events closes the gap, because a request is counted the moment it's issued, not the moment it completes.

Cloudflare's WriteGuard addresses a related but distinct problem: even a correct per-server policy doesn't help if an organization runs many MCP servers and each one implements its own version of "what counts as a risky write." WriteGuard centralizes that as a shared layer behind Cloudflare's MCP portal, assigning every operation one of four risk tiers (read-only, minimal impact, contained write, critical) so the tiering logic lives in one place instead of being reimplemented, inconsistently, per server.

## Evidence
- Story-backed (AWS Dogwood): AWS's own open-source release describes the temporal extension mechanism, its four operators, and gives a concrete worked example of the request-vs-response concurrency trap, alongside an explicit caveat that the reference interpreter isn't production-ready and that temporal conditions give up Cedar's formal-verification guarantees.
- Story-backed (Cloudflare WriteGuard): Cloudflare's own announcement of a shared MCP write-action policy layer, including its risk-tier scheme and rationale, but currently in private beta with no measured production results reported.
- Editorial inference: that these two, independently built in the same window, both target "per-request checks aren't enough for agents acting in sequence" is LLM Digest's synthesis, not a claim either source makes about the other.

## How to apply
- **Before writing a tool-call policy, decide explicitly whether it needs cross-call history.** Most authorization rules don't; approval workflows, rate/spend limits, and post-action sequencing rules do, and treating them as stateless checks is where this class of bug comes from.
- **If a rule counts events, count them at the moment they're issued, not the moment they settle.** Dogwood's own example — a spend cap defeated by concurrent in-flight requests — is a direct consequence of counting responses instead of requests; the same trap applies to any rate limit or budget check you write yourself, with or without Dogwood.
- **Use Dogwood's four operators as vocabulary even if you don't adopt Dogwood itself**: "did X happen in this window," "how many times," "how many distinct values," and "running total" are the shapes almost every stateful agent policy reduces to, and naming them explicitly makes it easier to spot which one a given rule actually needs.
- **Don't treat a reference interpreter or private beta as a production authorization engine.** AWS says so explicitly for Dogwood's interpreter, and Cloudflare has no production track record yet for WriteGuard — both are evidence the problem is real and worth building for, not evidence either tool is ready to be your only control.
- **If you run many MCP servers, consider centralizing risk-tiering rather than letting each server define its own.** WriteGuard's stated motivation — reimplementing per-server controls produces inconsistent behavior — applies whether or not you use Cloudflare's product specifically.

## Failure modes
- Writing a rate limit, spend cap, or approval rule, testing it only against sequential single-call traffic, and shipping it without testing concurrent calls — the exact gap AWS's own worked example demonstrates.
- Counting the wrong event in a stateful check: summing responses instead of requests, or checking "has this happened" against a completed action instead of an issued one, so in-flight concurrency slips past a rule that looks correct in isolation.
- Assuming a stateless, per-request authorization system (classic RBAC, or Cedar without temporal extensions) can express "stop after this agent has already done X" at all — it structurally can't, no matter how the individual rule is tuned.
- Deploying a reference implementation or beta product as a production control because it addresses a real gap, without accounting for the maker's own caveats about its production-readiness.

## Related
See [MCP](/topic/mcp) for the protocol both Dogwood and WriteGuard govern tool calls within, [agent sandboxing](/topic/agent-sandboxing) for execution-isolation controls that operate at a different layer than authorization policy, and [tool use](/topic/tool-use) for the broader pattern of ad-hoc agent-tool integrations this kind of policy gap grows out of.
