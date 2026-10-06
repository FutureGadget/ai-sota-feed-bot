---
title: "deptrust lets coding agents check package versions for known vulnerabilities"
date: 2026-07-03
theme: drift-tooling
evidence: [8db233accb157cb2]
---
**deptrust** checks package versions for known vulnerabilities across npm, PyPI, crates.io, Go modules, Maven, GitHub Actions, and more, as a local CLI and an MCP server calling public registry and OSV APIs directly. Its author built it because coding agents kept suggesting outdated or vulnerable versions.

An agent's knowledge of the ecosystem drifts out of date. A verification tool in the loop corrects it at suggestion time.
