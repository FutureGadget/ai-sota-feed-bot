---
title: "A 149M on-device model answers 70% of phone-agent steps and hands the rest to a frontier model"
date: 2026-11-19
theme: routing
evidence: [eef9b762f0728ea7]
---
Milo Pointer is a **149M-parameter** first tier for phone agents: it answers the steps it is confident about and routes the rest to Claude, with the routing rule pre-registered before evaluation. On 1,000 held-out AndroidControl steps (offline, one step at a time), it handles about **70%** locally. All Claude calls behind the results cost **$86.75** at batch prices, and a training run takes about 6.4 hours on one T4. Results are author-reported.

For builders: confidence-gated cascades work below the "small model" sizes usually discussed, and publishing per-step outputs plus the registration log is the bar for trusting a routing claim.
