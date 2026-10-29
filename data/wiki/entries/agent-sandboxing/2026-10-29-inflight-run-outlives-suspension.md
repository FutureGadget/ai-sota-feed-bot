---
title: "Agent runs started before a user suspension kept writing files, failing 2 of 14 checks"
date: 2026-10-29
theme: permission-policy
evidence: [400904d310baccd7]
also: [agent-reliability]
---
Scopehaven, a vendor selling agent security testing, reports a pilot on an unnamed open-source AI workspace using synthetic data (vendor-reported, one pinned version). After a test user was suspended, new requests were refused, but in 2 of 14 cases a run begun earlier still wrote a file. The team found it by reading the file on disk, not the next response.

The cause is a general pattern: authorization is checked once at run start, while agents keep calling tools, waiting on approvals, or resuming from queues. A partial local repair passed 14 of 14, verified only on the file-write path. Re-check authority before each side-effecting tool call.
