---
title: "Grab's Palana runs agents on a Kubernetes platform with proxy-mediated, Vault-backed secrets"
date: 2026-06-26
theme: managed-platforms
evidence: [8a98677361367a46]
---
Grab's security team built **Palana**, a Kubernetes-native secure execution platform, on the premise that model-driven agents show unpredictable tool use, code writing, and injection risk that deterministic software does not. It contains them at the infrastructure level with **isolated namespaces, out-of-process control planes, and proxy-mediated, Vault-backed secrets**.

Sandboxing, scoped access, and central governance arrive as paved-road infrastructure a platform team operates, not per-agent setup.
