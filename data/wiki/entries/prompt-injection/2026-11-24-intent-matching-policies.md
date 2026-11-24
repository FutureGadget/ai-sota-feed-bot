---
title: "Checking each tool call against the user's request cut AgentDojo hijacks from 48.7% to 0.9% (vendor-reported)"
date: 2026-11-24
theme: harness-controls
evidence: [d0ed4d1f645598f1]
also: [tool-use]
---
Google's Semantic governance policies check every proposed tool call, before it runs, against natural-language policies and against what the user actually asked for. In an AgentDojo banking task with an injected payment instruction in a bill file, the unguarded agent paid the attacker in **6 of 6 runs**. With user-intent matching on, Google reports attack success falling from **48.7% to 0.9%** at a **2.6-point** utility cost (vendor-reported).

For builders: the defense sits at the action, not the input. An intent check before high-impact calls catches injections that a content filter on retrieved text would let through.
