---
title: "Claude Code tags workflow-spawned agents with OpenTelemetry run IDs"
date: 2026-07-07
theme: trace-capture
evidence: [863330601bd5d524]
---
claude-code v2.1.202 adds **`workflow.run_id` and `workflow.name` OpenTelemetry attributes** to telemetry from workflow-spawned agents, so a workflow run's activity can be reconstructed from OTel data.

A multi-agent run becomes traceable through the OTel pipeline a team already operates, with no bespoke exporter.
