---
title: "Binding tool-call arguments to a user intent contract cut attack success from 50.5% to 12.0%"
date: 2026-11-24
theme: harness-controls
evidence: [991a99f085089c64]
---
*IntentFlow* targets arguments that come from a trusted tool but were never authorized by the user, such as an account number read from an email. A mediation layer checks each argument against an intent contract derived from the request and against its provenance. On a synthetic benchmark, attack success fell from **50.5% to 12.0%**, and no benign task was wrongly blocked.

For builders: allowlisting the tool is not enough when the attacker controls a parameter. Track where each argument value came from and require that high-risk ones trace back to the user's own request.
