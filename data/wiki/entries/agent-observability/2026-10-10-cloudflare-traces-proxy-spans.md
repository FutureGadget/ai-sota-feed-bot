---
title: "Cloudflare Traces emits proxy-layer steps as OpenTelemetry spans that join your agent traces"
date: 2026-10-10
theme: trace-capture
evidence: [c96d66505e1261e7]
---
Cloudflare put Traces into open beta, extending automatic tracing beyond Workers to security rules, transformations, cache, routing, and origin handling, all as **OpenTelemetry spans**. It accepts and forwards W3C `traceparent` headers, so edge spans attach to the trace your agent harness already started. **Trace Rules** sample selectively.

For builders, tool calls and model-gateway traffic that cross the edge no longer break the trace at the proxy. Pricing moves to **ingestion and retention volume from December 1**, so budget for span volume from agent loops before enabling it broadly.
