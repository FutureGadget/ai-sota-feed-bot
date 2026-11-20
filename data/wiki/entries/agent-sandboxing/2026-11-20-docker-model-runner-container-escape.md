---
title: "Docker Model Runner's unauthenticated API let a default container corrupt the Docker Desktop VM"
date: 2026-11-20
theme: local-sandboxes
evidence: [818a7b201aa40d45]
also: [prompt-injection]
---
ZDI reported CVE-2026-28400 in Docker Model Runner, the local model server built into Docker Desktop. An **unauthenticated argument-injection** flaw let a container with default privileges overwrite and corrupt the Docker Desktop VM's data disk. Further analysis under non-default settings extended this toward container escape.

For builders running agents in local containers: a local inference server is part of the sandbox's attack surface. A container that can reach the model runner's API can attack the host VM, so block that endpoint from agent containers and patch Docker Desktop.
