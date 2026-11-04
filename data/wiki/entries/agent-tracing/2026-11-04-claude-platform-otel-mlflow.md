---
title: "Claude Platform exports native OpenTelemetry traces to Databricks MLflow"
date: 2026-11-04
theme: capture
evidence: [4db92d07b6f4ba7b]
---
Databricks announced that MLflow is now a supported destination for native OpenTelemetry export from the Claude Platform. Traces of model and tool calls land beside existing MLflow data, so teams can find recurring failures, such as an agent rereading the same source, and test whether a change helps.

For builders: OpenTelemetry export means trace capture needs no custom SDK, and the backend stays swappable. This is a vendor announcement; check span coverage on your own agents.
