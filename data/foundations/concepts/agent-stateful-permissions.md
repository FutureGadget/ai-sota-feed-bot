---
slug: agent-stateful-permissions
title: "Why can a permission check that's correct for a single tool call still let an agent break the rules across many?"
question: "Why can a permission check that's correct for a single tool call still let an agent break the rules across many?"
summary: "A policy that checks each tool call in isolation can be right every time and still let an agent break a limit across a sequence. AWS's Dogwood shows a $5,000 cap beaten by three concurrent $2,000 transfers when it counts settled responses, not issued requests."
status: active
cluster: safety
updated: 2026-10-06
audience: "strong-software-engineer"
related_topics: [mcp, agent-sandboxing, tool-use]
related_playbook_cards: []
related_storylines: []
evidence:
  - id: story-410ca031ddd240de-aws-dogwood
    kind: story
    sid: "410ca031ddd240de"
    title: "AWS Open-Sources Dogwood, Extending Cedar to Govern Sequences of Agent Tool Calls"
    added: 2026-08-22
    note: "AWS open-sourced Dogwood (Apache 2.0), a Cedar extension adding a `when temporal` clause that reads agent event history. Four operators, macros over Metric First-Order Temporal Logic: formerly, count_within, count_distinct_within, sum_within. Worked example: a $5,000 cap summing settled responses is beaten by three concurrent $2,000 transfers; count requests as issued instead. Caveats: the reference interpreter is not for production, and temporal conditions give up Cedar's automated formal-analysis guarantees."
  - id: story-e3560887ce822a61-cloudflare-writeguard
    kind: story
    sid: "e3560887ce822a61"
    title: "Cloudflare WriteGuard Brings Fine-Grained Security Controls for MCP Servers"
    added: 2026-08-22
    note: "Cloudflare WriteGuard, in private beta with no production results reported, sits behind Cloudflare's MCP server portal as a shared policy and audit layer. It intercepts MCP tool calls and assigns each operation a risk tier: read-only, minimal impact, contained write, or critical. Stated rationale: reimplementing controls in each server 'would take more work and produce inconsistent behavior.'"
  - id: agent-stateful-permissions-editorial-synthesis
    kind: editorial-inference
    title: "LLM Digest synthesis"
    added: 2026-08-22
    note: "Dogwood and WriteGuard attack the same gap from different sides. Dogwood puts cross-call state into the policy language; WriteGuard centralizes per-operation risk tiering so many MCP servers share one enforcement point. Neither is a proven production control yet, but both are independent 2026 evidence that per-request authorization is no longer treated as enough for agents acting in sequences."
---

## Builder consequence
If your tool-call authorization checks each request in isolation (classic RBAC, and Cedar's default), a policy can be correct for every single call and still let the agent do what it was meant to prevent. AWS's example: a **$5,000** transfer cap, checked correctly per request, falls to three concurrent **$2,000** transfers. The cap logic is fine. The bug is enforcing a stateful rule with a stateless check.

## Short answer
Rules about what an agent has already done (approval before acting, rate or spend limits, "stop after touching confidential data") need the agent's event history, not just the current request. AWS's Dogwood adds a `when temporal` clause to Cedar with four history operators. What the rule counts matters as much as the operator. Counting *settled responses* lets several *in-flight requests* each pass before any of them updates the total.

## Builder model
Split authorization into two questions that need different mechanisms:

- **Is this request allowed on its own?** A stateless check of caller, action, and resource answers it. Most tool calls only need this.
- **Is it allowed given what the agent already did?** Approval workflows, rate or spend limits, and sequencing rules need history. A stateless check cannot answer this however you tune it.

Even history-aware checks fail when they count the wrong event: completed actions instead of issued ones.

## Mechanism
**Why stateless is the default.** Cedar evaluates a request using only its own context: principal, action, resource, and attributes. That restriction is what lets Cedar formally verify a policy set, for example that no request is both permitted and denied, without simulating every call sequence.

**How Dogwood adds history.** A `when temporal` clause is translated into ordinary Cedar context fields, filled from the event history, before the stateless evaluator runs. Temporal reasoning happens once, up front. Four operators cover the common shapes:

- `formerly`: did X happen in a window?
- `count_within`: how many times?
- `count_distinct_within`: how many distinct values?
- `sum_within`: what is the running total?

The cost is that temporal conditions give up Cedar's automated formal-analysis guarantees.

**The concurrency trap.** `sum_within(response.amount, 1h) <= 5000` passes every sequential test. Under concurrency, three $2,000 requests are each evaluated while the settled total is still $0, so all three pass. Writing the rule against request events closes the gap, because a request counts the moment it is issued.

**Consistency across servers.** A correct policy on one MCP server does not help if every server defines "risky write" differently. Cloudflare's WriteGuard centralizes that into one layer with four risk tiers, from read-only to critical.

## How to apply
- **Decide up front whether a rule needs history.** Approval workflows, rate or spend limits, and post-action sequencing rules do. Most others do not.
- **Count events when they are issued, not when they settle.** This applies to any budget or rate limit you write, with or without Dogwood.
- **Use the four operator shapes as vocabulary** to name which kind of history a rule needs, even without adopting Dogwood.
- **Test stateful rules with concurrent calls,** not only sequential ones.
- **Do not make a reference interpreter or private beta your only control.** AWS says Dogwood's interpreter is not for production; WriteGuard has no production track record.
- **Centralize risk tiering** if you run many MCP servers, instead of letting each server define its own.

## Failure modes
- Testing a spend cap or rate limit only with sequential traffic, then shipping it.
- Summing responses instead of requests, so in-flight calls slip past a rule that looks correct.
- Expecting a stateless system (classic RBAC, plain Cedar) to express "stop after the agent did X".
- Deploying a reference implementation or beta as a production control despite the maker's own caveats.

## Related
See [MCP](/topic/mcp) for the protocol both tools govern, [agent sandboxing](/topic/agent-sandboxing) for isolation controls at a different layer, and [tool use](/topic/tool-use) for the agent-tool integrations where this gap appears.
