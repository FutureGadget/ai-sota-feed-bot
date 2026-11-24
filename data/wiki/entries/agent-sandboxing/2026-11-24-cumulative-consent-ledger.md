---
title: "Approving each action separately misses forbidden workflows; a ledger of cumulative consequences caught 89.2%"
date: 2026-11-24
theme: permission-policy
evidence: [3b43d55ebb701383]
also: [prompt-injection]
---
*When a Permitted Action Completes a Forbidden Workflow* targets chains in which every step is allowed but the sequence is not, such as reading a file and then emailing it out. The proposed **Cumulative Consent Ledger** shows approvers the combined consequences of the action chain instead of one call at a time. An 80-participant study tested the interface, and an automated monitor detected **89.2%** of violating checkpoints.

For builders: per-call allowlists cannot express "not both". Track the chain's accumulated effects and show them at each approval prompt.
