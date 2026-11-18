---
title: "A loose version range pulled a credential stealer from Microsoft's agent-framework PyPI package"
date: 2026-11-18
theme: transitive-pinning
evidence: [513557a2b1748d59, 30e3fc959dd5093e, e0e72401db1a67ac]
also: [agent-sandboxing]
---
On Nov 17, `agent-framework` **1.26.1 and 1.26.2**, Microsoft Agent Framework's PyPI meta-package, shipped 33 minutes apart with a `.pth` startup hook. The hook runs on every Python start, so nothing has to import the package. It took environment variables and credential files, then asked Azure DevOps, Azure managed identity and GitHub Actions for fresh tokens and sent them to a webhook. Both releases were pulled. SafeDep flagged the first one 22 minutes after it was published.

A requirement like `agent-framework>=1.26` was enough to be hit. For builders: pin agent frameworks to exact versions with hashes, and keep CI installs out of jobs that hold cloud and deploy secrets. Anyone who installed either release should pin 1.26.0 and rotate every secret on that machine.
