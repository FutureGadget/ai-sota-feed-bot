---
title: "Cloudflare lets an agent deploy to a temporary account that expires in 60 minutes"
date: 2026-06-22
theme: credential-boundary
evidence: [ed140b4e4c38f7b0]
---
`npx wrangler deploy --temporary` deploys a Workers project to a **new, ephemeral project that stays live for 60 minutes**, with no Cloudflare account or standing login.

Simon Willison notes the "for AI agents" framing is partly marketing: it is a general feature. It is still exactly the short-lived, least-privilege primitive agents need, a self-expiring boundary instead of handing an agent your real account keys.
