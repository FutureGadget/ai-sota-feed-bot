---
title: "Morph Reflexes scores many failure modes in one pass over a trace"
date: 2026-07-01
theme: cheaper-judges
evidence: [cf0a37dd32efaf51]
---
Morph Reflexes reads an agent trace once through a shared backbone and scores behavioral signals — looping, reasoning leakage, user frustration — with **separate classifier heads off the same forward pass**.

Reusing the KV cache gives sub-30ms inference and under 2ms of marginal latency per added signal, so "judge every failure mode" costs one read of the trace instead of N model calls.
