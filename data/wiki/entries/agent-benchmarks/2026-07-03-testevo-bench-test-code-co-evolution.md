---
title: "TestEvo-Bench checks whether agents update tests along with the code they change"
date: 2026-07-03
theme: domain-suites
evidence: [33347a0b1de54b78]
---
**TestEvo-Bench** is an executable, live benchmark of test-and-code co-evolution tasks mined from real repositories. Unlike benchmarks that isolate the test from the code change or rely on static metadata, it verifies that generated tests run and are semantically tied to the change.

It isolates a habit coding agents need in production: keeping the test suite in sync with what they modify.
