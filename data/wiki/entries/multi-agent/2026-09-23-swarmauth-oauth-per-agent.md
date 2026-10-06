---
title: "SwarmAuth applies OAuth 2.1 to scope credentials per agent in a swarm"
date: 2026-09-23
theme: oversight-and-safety
evidence: [0eda69d97282c3b4]
---
SwarmAuth, a Python package, proposes **OAuth 2.1 for AI agent swarms**: credentials scoped and granted per agent identity instead of one broad credential shared across the mesh.

It is the authorization primitive behind the "distinct credentials per agent role" advice, so a compromised or misbehaving agent can only do what its own grant allows. Early project.
