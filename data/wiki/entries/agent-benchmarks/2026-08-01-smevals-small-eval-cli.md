---
title: "smevals turns building a small eval suite into a CLI command"
date: 2026-08-01
theme: own-workload
evidence: [59c692b9d0ccdcdf]
---
Simon Willison and Jesse Vincent's Prime Radiant lab built **smevals**, a tool for running small eval suites across model configurations and grading results. `uvx smevals run/grade/serve` builds, runs, and grades a directory of YAML eval files, and a coding agent can author the suite from `uvx smevals docs`.

It drops the cost of "benchmark on your own tooling" from a bespoke harness to a reusable command.
