---
title: "A honeypot page got Claude's web_fetch to follow nested links and leak user details"
date: 2026-07-15
theme: injection-paths
evidence: [5201cdda51e234b5]
---
Ayush Paul found a hole in the exfiltration defenses of Claude's `web_fetch` tool. A honeypot page disguised as a Cloudflare login, triggered only when it detected a Claude client's user agent, got the tool to keep following attacker-generated links nested in content it had already fetched. It leaked the user's **name, home city, and employer**. Anthropic closed it by stopping `web_fetch` from following links returned within its own fetched content.

The injected instruction never arrived as a prompt. It arrived inside content the tool had fetched on the model's behalf, so tool output needs the same distrust as user input.
