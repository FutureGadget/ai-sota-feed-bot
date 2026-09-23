---
slug: scalability
kind: obstacle
title: "Agent infrastructure buckles under concurrency, not just load"
area: scalability
status: active
solutions: [agent-sandboxing]
obstacles: []
related_storylines: []
evidence: [485666e1560ba32b, 6a60d1242802c6f9]
updated: 2026-09-23
covers_evidence: [485666e1560ba32b, 6a60d1242802c6f9]
---

## TL;DR
A single agent is a serving problem; a fleet of agents is a distributed-systems
problem. Every agent that spins up a sandbox, holds a serving slot, or opens a
session adds concurrent, short-lived state — and the coordination layer meant
to track that state, not raw compute, is what breaks first at agent-native
scale.

## State of the art
Two vendors hit the same wall from different directions and answered it the
same way: stop treating agent concurrency as a bigger version of the old
problem, and remove the central coordinator instead of scaling it.

Modal rebuilt its sandbox infrastructure after finding that Kubernetes-style
orchestration — a centrally coordinated scheduler backed by strongly
consistent state in etcd — caps out well short of what agent workloads need:
etcd can't be sharded within a keyspace, and scheduling and node-management
operations scale with the number of containers and nodes, so the coordinator
itself becomes the bottleneck long before the hardware does. Their rebuild
removes the central coordinator entirely: a horizontally scalable fleet of
scheduling servers load-balances requests instead of routing every decision
through one source of truth, each worker accepts or rejects a sandbox
creation directly over RPC based on its own available resources, and workers
publish state to a single Redis stream that the team expects to hold up past
100,000 workers. The result is a system that created 1 million concurrent
sandboxes in under 60 seconds, sustained roughly 50,000 sandbox creations per
second, and brought median cold-start (startup-to-running-code) latency under
0.5 seconds — evidence that removing the coordinator, not adding more of it,
is what unlocks concurrency at this scale.

The serving layer is hitting the same concurrency pressure from the inference
side: vLLM's new vllm-metal brings vLLM's scheduler and paged KV cache to
Apple Silicon (M1 Pro through M5 Pro), replacing padded batching with a
"packed queries" design that concatenates request tokens into one ragged
batch instead of padding every request to the same length — a directly
concurrency-shaped fix, since padding overhead compounds as more concurrent
requests share a batch. The paged KV cache's per-request block tables carry
the same benefit further: fixed-size pages let variable-length sequences
share memory without reshaping the cache, which is what makes admission
control practical under concurrent load in the first place.

## What's new
Modal published the engineering account of rebuilding its sandbox scheduler
around per-worker autonomy instead of central coordination, reaching 1
million concurrent sandboxes and sub-second cold starts; vLLM's vllm-metal
brought the same paged, concurrency-aware serving design to Apple Silicon the
same week (see State of the art above).

## Why it matters for platform engineers
Concurrency is a different failure mode than throughput, and it shows up
first in the layer a team is least likely to have load-tested: the scheduler
or coordinator that tracks which sandbox, session, or KV-cache page belongs
to which agent. A platform built to serve one agent well can still fall over
the moment a thousand agents run at once, because the bottleneck was never
the model call — it was the shared, strongly consistent state every request
had to pass through. Budget for concurrent state (sandbox lifecycle, session
tracking, KV-cache admission), not just aggregate request volume, and prefer
architectures where each worker can make a local decision over ones that
route every request through one coordinator (see [agent
sandboxing](/topic/agent-sandboxing) for the isolation side of the same
sandbox-fleet problem).
