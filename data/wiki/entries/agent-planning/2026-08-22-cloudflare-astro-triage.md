---
title: "Cloudflare cut Astro's GitHub issue load 85% by wrapping agents around triage"
date: 2026-08-22
theme: loop-as-infrastructure
evidence: [503c543dadac240a]
---
Per InfoQ, Cloudflare cut GitHub issue-triage work on the **Astro** project **85%** with AI agents built into the workflow via GitHub Actions, Cloudflare Workers, and Flue, with humans kept in the loop.

It is a measured production case for wrapping a structured workflow around the model rather than routing raw model calls at each issue.
