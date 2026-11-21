---
title: "A malicious npm package installed Hermes Agent as a root service controlled over Telegram"
date: 2026-11-21
theme: transitive-pinning
evidence: [3b3617abd2209071]
also: [prompt-injection]
---
`@leadstack/crm-connect` posed as an official CRM client. On install it set up **Hermes Agent**, downloaded its keys and standing instructions from the attacker's server, connected it to a Telegram bot, and registered it as a systemd service disguised as a "Lead Routing Daemon". Run under root, the agent got root shell, file, and browser control.

Nine versions shipped on 16 November; SafeDep flagged it five minutes after the last, and npm removed it. The publisher's newer packages pull code from a remote server at install time. For builders: an off-the-shelf agent is now the implant, so pin by hash, block install scripts, and never run `npm install` as root.
