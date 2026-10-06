---
title: "Loka's Nova 2 Sonic voice agent treats round-trip time as a design constraint"
date: 2026-06-30
theme: beyond-the-engine
evidence: [c66b542cadbb4592]
---
Loka built a voice agent on Amazon Nova 2 Sonic to fix a specific failure: **slow, robotic voice assistants make customers hang up**, which damages the brand and drives up support costs. The architecture treats round-trip time as a first-class constraint from the start, not a tuning pass afterwards.

Interactive modes set a hard latency floor. A voice agent's budget is set by when the caller gives up, not by what the serving stack happens to deliver.
