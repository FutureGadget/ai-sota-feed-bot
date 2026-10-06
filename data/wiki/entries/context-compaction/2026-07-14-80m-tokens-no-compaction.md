---
title: "One agent session runs 80M tokens of Terminal-Bench 2.0 with no compaction and no accuracy loss"
date: 2026-07-14
theme: skipping-compaction
evidence: [8561672eafb892cc]
also: [agent-memory]
---
A team ran a single agent session through **all 89 sequential Terminal-Bench 2.0 tasks**, over 80 million tokens, with no compaction. They report no measurable accuracy loss versus giving each task a fresh session.

Their case against compaction: 300,000 tokens of work cannot survive a sub-20,000-token summary, and one model alone decides what is worth keeping, which invites hallucination and bias. This is a practitioner result on one benchmark, but it is measured across a real multi-task run, not a synthetic long-context probe.
