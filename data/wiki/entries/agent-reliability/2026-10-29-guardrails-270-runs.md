---
title: "Guardrails did not raise first-pass rates in 270 coding-agent runs, but caught defects at done"
date: 2026-10-29
theme: verifying-the-work
evidence: [524f8aff53aebfdc]
---
A single-author experiment (self-run, small sample) ran Claude Code across three models and seven tasks under three conditions: nothing, an instruction file, and instruction file plus pre-commit gate and stop hook. All 270 runs were eventually accepted and 267 passed hidden tests first time, so guardrails did not move the pass rate.

They changed what runs left behind. On the four harder tasks, 9 of 60 gated runs left a defect against 15 of 60 ungated, a gap too small to call. The clearer signal: without the rule file, 14 of 15 runs changed a schema without its required test; with it, none of 30 did.

Judge guardrails on defects at "done", not on pass rate.
