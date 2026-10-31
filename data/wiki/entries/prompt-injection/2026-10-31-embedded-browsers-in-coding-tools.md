---
title: "Embedded browsers in five AI coding tools could run commands, read local files, or spoof the address bar"
date: 2026-10-31
theme: harness-controls
evidence: [e5726bf03a816877]
also: [agent-sandboxing]
---
Forever Security's EMBRACE research (published Oct 29, researcher-reported; this write-up is a secondary summary) found that the browsers built into five AI coding tools broke three basic browser rules: a page must not run programs, a local file must not read other files, and only the browser writes the address bar.

The attack surface is the page an agent or user opens, not the model. Treat an IDE's embedded browser as an untrusted renderer: check each vendor's patch status, avoid opening untrusted pages in it, and search your projects for the published indicators of compromise.
