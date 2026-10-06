---
title: "Agora allocates sub-tasks to expert models and tools by auction"
date: 2026-07-13
theme: when-it-pays
evidence: [d02ebf5c5a48e6af]
---
Agora replaces the coarse-grained matching a main agent uses to route sub-tasks with an **incentive-compatible auction**: candidate models and tools bid for each task, and allocation accounts for performance variability and cost among functionally similar options.

Fixed routing tables ignore exactly those differences. "Which agent handles this" becomes a market-clearing problem rather than a lookup.
