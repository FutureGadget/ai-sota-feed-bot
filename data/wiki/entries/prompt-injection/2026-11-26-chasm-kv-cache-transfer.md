---
title: "Transferring KV caches between models in multi-agent systems raises prompt-injection and jailbreak success"
date: 2026-11-26
theme: injection-paths
evidence: [e5cd4c9ff569d569]
also: [multi-agent]
---
Some multi-agent systems now pass KV caches between models instead of text, to skip re-encoding. The Chasm study finds this latent channel is an attack path: a transferred cache can raise prompt-injection and jailbreak success on the receiving model. The authors propose a target-side guard that checks incoming caches.

For builders: latent communication bypasses text-level filters that inspect messages between agents. If you adopt cache sharing, treat a received cache as untrusted input and guard it on the receiving side.
