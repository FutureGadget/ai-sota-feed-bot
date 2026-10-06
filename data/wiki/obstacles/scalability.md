---
slug: scalability
kind: obstacle
title: "Agent infrastructure buckles under concurrency, not just load"
area: scalability
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: []
updated: 2026-10-06
themes:
  - key: coordinator-free-scheduling
    title: Removing the central coordinator instead of scaling it
    summary: Sandbox schedulers and the MCP protocol both drop central, strongly consistent coordination so each worker or request decides locally and scales horizontally.
  - key: concurrent-serving
    title: Serving many agents at once without padding waste
    summary: Paged KV caches and packed, ragged batching keep time to first token flat as concurrent agent requests share a batch, now down to Apple Silicon.
  - key: fleet-density
    title: Sandbox density and scale-to-zero for idle fleets
    summary: Platforms now suspend idle agent sandboxes and resume them in under a second, so idle fleets stop holding capacity; density claims are vendor-reported.
---

## TL;DR
A single agent is a serving problem; a fleet of agents is a distributed-systems
problem. Every agent that spins up a sandbox, holds a serving slot, or opens a
session adds concurrent, short-lived state. The coordination layer that tracks
that state, not raw compute, is what breaks first at agent-native scale.

## State of the art
**The consensus fix is to remove the central coordinator, not scale it.** The
same move now shows up at three layers:

- **Sandbox scheduling.** A Kubernetes-style scheduler backed by strongly
  consistent state caps out before the hardware does. The working design lets
  each worker accept or reject work on its own resources and publish state to
  a shared stream. Modal reports 1 million concurrent sandboxes in under 60
  seconds this way.
- **Inference serving.** Paged KV caches and packed, ragged batching stop
  padding overhead from compounding as concurrent requests share a batch.
- **Tool protocol.** Stateless MCP drops sessions and sticky routing so remote
  servers scale like any stateless service.

**Density is the second lever.** Instead of keeping sandboxes warm, platforms
suspend idle ones and resume them in under a second, and Kubernetes can now
scale agent workloads to zero.

**The open problem is where the state goes.** Removing the coordinator or the
session does not remove the state. Retries, idempotency, application state,
and observability move to layers the platform team now owns. Most published
numbers are vendor-reported and not independently reproduced.

## Why it matters for platform engineers
Concurrency fails differently from throughput, and it fails first in the layer
teams rarely load-test: the scheduler or coordinator that tracks which
sandbox, session, or KV-cache page belongs to which agent. A platform that
serves one agent well can still fall over when a thousand run at once.

Budget for concurrent state (sandbox lifecycle, session tracking, KV-cache
admission), not just aggregate request volume. Prefer designs where each worker
decides locally over ones that route every request through one coordinator. See
[agent sandboxing](/topic/agent-sandboxing) for the isolation side of the same
fleet problem.
