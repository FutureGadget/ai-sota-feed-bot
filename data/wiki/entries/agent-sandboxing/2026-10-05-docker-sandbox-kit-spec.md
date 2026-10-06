---
title: "Docker brings its Sandbox Kit Spec to the CNCF, packaging agent permissions as OCI images"
date: 2026-10-05
theme: permission-policy
evidence: [a69bd0ab88575726]
---
Docker is taking the **Sandbox Kit Specification** to the CNCF. It packages what an agent may access as an **OCI image**, so the grant travels with the agent between runtimes instead of living in each runtime's config.

If adopted, permissions become a versioned, reviewable artifact in the same registry and pipeline as the agent image.
