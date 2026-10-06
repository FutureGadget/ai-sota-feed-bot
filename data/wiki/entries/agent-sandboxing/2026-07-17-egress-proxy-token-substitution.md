---
title: "Managed agents use the GitHub CLI with a dummy token; the egress proxy injects the real one"
date: 2026-07-17
theme: credential-boundary
evidence: [ea758b7fe7cc27d3]
---
Philipp Schmid shows Gemini Managed Agents calling the GitHub CLI **without the personal access token ever entering the sandbox**. The sandbox sees only a dummy token; an egress proxy swaps in the real credential on outbound requests.

A prompt-injected agent can still misuse the tool while the session runs, but it cannot read or exfiltrate the token itself.
