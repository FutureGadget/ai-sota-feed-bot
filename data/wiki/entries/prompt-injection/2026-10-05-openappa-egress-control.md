---
title: "Archestra's OpenAPPA blocks exfiltration at the data-flow layer, with vendor-reported 0% attack success"
date: 2026-10-05
theme: harness-controls
evidence: [36b791854c0867eb]
---
Archestra's open-source OpenAPPA targets the **exfiltration step** of prompt injection or hallucination rather than detecting the injection itself. Archestra reports zero successful attacks on Bench-Corp (20 multi-step enterprise workflows) and AgentThreatBench, against 10% for Claude Code's auto mode and 31% for Microsoft FIDES.

These are vendor-run numbers on two benchmarks. Read them as a design signal (enforce at the data-flow boundary), not as proof of immunity.
