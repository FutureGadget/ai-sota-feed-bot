---
title: "Google tests Chrome's browsing agents in a controlled replica web seeded with hidden injections"
date: 2026-11-25
theme: adversarial-and-security
evidence: [a9933de7f7b7b312]
also: [prompt-injection]
---
Google's Chrome team built the **Mirror Dimension**, an isolated web it fully controls, with social, shopping, and bank-dashboard sites built like real ones. Gemini browsing agents complete tasks there as they would online while facing resilience tests such as hidden prompt-injection attacks. The realism targets *eval awareness*: models that detect a test can behave differently, and narrow test sites train poorly, while the open web is unsafe for unrefined agents.

For builders: a web agent's safety eval needs realistic, controllable targets. Toy pages under-test injection and invite eval-aware behavior.
