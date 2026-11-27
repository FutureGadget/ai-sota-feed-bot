---
title: "Per-command sandbox billing prices an hour-long, 120-call agent session at $0.006 versus ~$0.067 per vCPU-hour"
date: 2026-11-27
theme: managed-platforms
evidence: [f613c86fe92edbd9]
also: [agent-cost]
---
Flashbox gives each agent conversation a Linux sandbox and bills per command at $0.05 per 1,000. Idle time is free. Heavy installs and builds move to a full-speed machine that keeps the same files. Its own comparison prices an hour with 120 short tool calls at **$0.006**, against about **$0.067** at E2B's list price for 1 vCPU and 1 GiB held for the hour (vendor-reported, prices checked 2026-11-23).

For builders: most of an agent session is the model thinking or a human reading. Under per-second billing, you pay for that idle box. Model sandbox cost from your real call rate, not from session length.
