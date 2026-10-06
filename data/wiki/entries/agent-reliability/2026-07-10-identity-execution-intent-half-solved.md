---
title: "Agent identity, reliable execution, and intent are each only half-solved"
date: 2026-07-10
theme: execution-and-identity
evidence: [6e5085e3c3e072bd]
---
An essay splits agent reliability into three legs:

- **Identity** has no purpose-built primitive. Platforms retrofit workload identity: SPIFFE-based identities (Gemini Enterprise), service principals plus token brokers (Microsoft Entra). The fit is poor because two runs of the same agent can behave differently.
- **Execution** borrows the distributed-systems playbook: checkpoint recovery, exactly-once guarantees, cgroup quotas, per-session microVM or gVisor isolation.
- **Intent** is least solved. Models drift from the task or report false completion. Fixes split between LLM-graded trajectory checks and cheaper encoder classifiers that score task completion, an auditability and cost trade-off.

The identity leg overlaps with [sandboxing and scoped credentials](/topic/agent-sandboxing).
