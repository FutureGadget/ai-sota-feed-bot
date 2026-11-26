---
title: "RecordRoute localizes a failed run's responsible actor and decisive step before naming the error mode"
date: 2026-11-26
theme: agentic-rca
evidence: [d8def057899f6ec1]
also: [agent-tracing]
---
RecordRoute is a supervised method for auditing failed agent runs. It first ranks the trajectory's records to pick the actor responsible and the decisive step. Only then does it predict the error mode, from that one record's text and metadata rather than the whole trace.

For builders: failure attribution works better as two steps, *where* then *what*. Structure trace records with actor and step metadata so a classifier, or a human, can point at one record instead of rereading a whole multi-agent trajectory.
