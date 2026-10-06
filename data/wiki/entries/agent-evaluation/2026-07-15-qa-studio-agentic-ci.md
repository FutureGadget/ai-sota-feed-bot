---
title: "AWS QA Studio runs browser-driving test agents as a parallel CI gate"
date: 2026-07-15
theme: eval-in-production
evidence: [fa7774ded73da0cc]
---
AWS's **QA Studio** (on Amazon Nova Act) runs agentic UI tests as parallel cloud tasks organized into suites, with a CLI for CI/CD. Runs return structured **pass / fail / infra-error** exit codes plus trajectory logs and session recordings.

Separating infra errors from real failures is what lets an agentic test sit in CI without flaky runs blocking merges.
