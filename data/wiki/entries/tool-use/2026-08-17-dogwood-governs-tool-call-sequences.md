---
title: "AWS Dogwood extends Cedar so policies can reason over an agent's tool-call history"
date: 2026-08-17
theme: guarding-the-call
evidence: [410ca031ddd240de]
---
AWS open-sourced **Dogwood** (Apache 2.0), which adds temporal operators to Cedar: `formerly`, `count_within`, `count_distinct_within`, `sum_within`. Rules can read prior tool calls instead of judging one request alone. It is supported in AgentCore Policy, but the reference interpreter is not production-ready.

The motivating case: a $5,000 transfer cap that checks settled responses is defeated by concurrency, because three simultaneous $2,000 requests all pass. The rule must count requests within a time window.

The cost is real: temporal evaluation needs stateful event tracking and gives up Cedar's automated formal-reasoning guarantees.
