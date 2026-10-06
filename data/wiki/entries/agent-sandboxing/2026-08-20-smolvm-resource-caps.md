---
title: "smolvm as a sandbox for untrusted code: cap RAM and CPU time, not just network and files"
date: 2026-08-20
theme: local-sandboxes
evidence: [f7dc95732d84964c]
---
Simon Willison had Claude research **smolmachines/smolvm** as a sandbox for running untrusted Python and JavaScript: hard limits on **RAM and CPU time** (the `while true` case), no network, and filesystem access only to designated files, for user-provided data transformations.

Resource exhaustion is its own containment axis. Most agent-sandbox discussion covers credentials and egress and leaves denial of service implicit.
