---
title: "Compiling web pages into typed operations lifts long-task completion to 76% from 46%"
date: 2026-11-25
theme: agent-native-surfaces
evidence: [84e1309d18f8c037]
also: [agent-cost]
---
Protocolis compiles a page's controls into typed operations on first visit, with no model inference, site-specific code, or prior visit. The model picks an operation; the compiler executes it, re-reads the page, and reports what changed, so the model never pays to read the page or check its last action. On long tasks every system attempted, it completed **76% (80/105)** versus **46%** for the best alternative, never fell below **55%** in any condition, and the cheapest alternative cost **1.9-26x** more per completed task. All numbers are author-reported.

For builders: when the site will not ship an agent surface, a deterministic compiler on your side can replace most per-step page reading.
