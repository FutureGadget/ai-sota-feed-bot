---
title: "AWS's Claude Apps Gateway relays telemetry and enforces spend caps from a self-hosted container"
date: 2026-07-15
theme: telemetry-ownership
evidence: [38f362bfcba6a0fa]
---
AWS and Anthropic released the **Claude Apps Gateway**, a single stateless container an organization runs in front of Claude Code and Claude Desktop. It centralizes identity, policy, routing, and telemetry, relays per-request usage metrics to the team's own OpenTelemetry collector (CloudWatch, Prometheus), and enforces YAML-defined spend caps by org, group, or user.

Telemetry relay and cost policy live in one customer-owned layer instead of a vendor dashboard.
