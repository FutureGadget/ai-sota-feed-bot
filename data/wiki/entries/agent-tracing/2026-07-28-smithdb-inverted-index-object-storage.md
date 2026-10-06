---
title: "SmithDB full-text-searches nested agent traces in object storage at 400 ms P50"
date: 2026-07-28
theme: storage
evidence: [f1059e8e95c865e9]
---
LangChain's SmithDB builds a **custom inverted index over object storage** so agent traces can be full-text searched and JSON-filtered directly. It reports a **400 ms median (P50)** query latency, even though each trace is a large, deeply nested JSON document.

At fleet scale, "traces are stored somewhere" is not enough: search over payloads is what makes them usable in an incident. This is the bar a self-hosted trace store has to meet.
