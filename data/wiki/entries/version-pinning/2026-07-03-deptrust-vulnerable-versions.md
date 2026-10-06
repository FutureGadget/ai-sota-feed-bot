---
title: "deptrust checks the package versions an agent picks against vulnerability databases"
date: 2026-07-03
theme: upgrade-tooling
evidence: [8db233accb157cb2]
---
**deptrust** is a CLI and MCP server that checks package versions for known vulnerabilities across npm, PyPI, crates.io, Go modules, RubyGems, Maven, GitHub Actions, and other ecosystems, calling public registry and OSV APIs directly with no hosted service. Its author built it because coding agents kept suggesting vulnerable versions.

A pin, or an upgrade an agent proposes, can be validated as safe, not just consistent.
