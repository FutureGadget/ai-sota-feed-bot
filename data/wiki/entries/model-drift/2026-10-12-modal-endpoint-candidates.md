---
title: "Modal Endpoint Candidates mirror sampled production traffic to a new model before promotion"
date: 2026-10-12
theme: drift-tooling
evidence: [0d0baaa970b0ad95]
also: [agent-evaluation]
---
Modal made Endpoint Candidates generally available: a staged alternative to a Dedicated Endpoint (a catalog model or your own weights) that receives a sampled copy of production requests while production still answers users. Each Candidate has its own URL, so existing evals run against it, and the dashboard shows latency and throughput. Promotion starts a rollout at the original endpoint URL.

Mirroring is best-effort: each mirror gets a bounded buffer in a Pingora-based proxy, and a slow or failing Candidate is cancelled rather than slowing production. Mirrored compute is billed at standard rates.

For builders: a checkpoint or model swap can be tested on real traffic first, but quality still needs your own evals.
