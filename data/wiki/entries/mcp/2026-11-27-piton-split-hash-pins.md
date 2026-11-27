---
title: "Piton pins MCP tool schemas and descriptions with separate hashes to catch third-party rug pulls"
date: 2026-11-27
theme: auth-and-governance
evidence: [bd26df9fc2790cc4]
also: [version-pinning, prompt-injection]
---
Piton writes a lockfile with two SHA-256 pins per MCP tool. A structural hash covers the name and input schema, and any drift is blocked. A description hash covers the prose the model reads. Drift there is blocked on third-party servers and only warns on internal ones, so a docstring typo fix does not break CI. It also flags tool-name shadowing across servers, hidden Unicode, and exfiltration directives. It lints Claude Code hooks, Cursor rules, and `.vscode` autorun tasks for `curl|sh`-style RCE. Runtime enforcement uses a wrapper and sidecar.

For builders: a tool description is executable input to the model. Pin third-party descriptions as strictly as schemas, and review every change.
