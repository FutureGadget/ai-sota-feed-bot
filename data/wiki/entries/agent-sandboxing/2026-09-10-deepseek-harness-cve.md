---
title: "CVE-2026-82533: a spoofed Host header let remote callers disable DeepSeek Harness's sandbox and approvals"
date: 2026-09-10
theme: egress-and-escapes
evidence: [8478102e21445d5c, 6d7e21b41e293e2d, 2454ea8187e26bdb]
---
DeepSeek's open-source Harness coding tool trusted a **client-supplied HTTP Host header** instead of the actual TCP peer, so a spoofed value made a remote request look like loopback. An unauthenticated caller could **disable file-write restrictions and approval prompts** and run privileged commands, with no API key, model call, or config change (CVSS 9.4). Version 0.1.2-alpha.1 fixed it with one-time-token API authentication.

The isolation can be sound and the approval gate still fail when the check for "is this caller trusted" is spoofable.
