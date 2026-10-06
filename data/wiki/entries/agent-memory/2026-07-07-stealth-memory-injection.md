---
title: "One email can plant a hidden memory that a personal agent acts on but never mentions"
date: 2026-07-07
theme: memory-integrity
evidence: [56ef11c9d3f8e424]
also: [prompt-injection]
---
"When Claws Remember but Do Not Tell" studies **stealth memory injection** in persistent personal agents. A remote black-box attacker sends a single email payload that must get the agent to write poisoned memory, stay hidden from the user in the agent's replies, and steer future behavior.

The planted entry need not look false, only concealed, so write-time checks aimed at obviously wrong facts may not flag it. Untrusted external content written to memory becomes trusted state later.
