---
title: "Dataflow pipelines escalate to a full agent only when an event needs judgment"
date: 2026-08-24
theme: caching-and-filtering
evidence: [cfb845e72338fcf2]
---
A Google Dataflow pattern combines Apache Beam streaming with the Agent Development Kit. The pipeline **escalates an event to a full gen-AI agent**, with database lookups and email tools, only when the event needs that judgment, such as an angry customer message. Everything else stays on the static path.

It controls cost at the entry point rather than inside the agent loop: the cheapest model call is the one a pre-filter decides not to make.
