---
title: "A protocol layer of versioned virtual tools with taint tracking to stop exfiltration"
date: 2026-07-24
theme: guarding-the-call
evidence: [eec5c9b0fcd373da]
---
Jake Mannix proposes an intermediate protocol layer that turns raw APIs into **versioned, encapsulated "virtual tools"**, with interface mapping, dynamic schema projection, and runtime taint tracking to catch data-exfiltration risk at the tool boundary.

This is one engineering leader's architecture, not a benchmarked result. It targets ungoverned tool sprawl through versioning and data-flow tracking rather than schema hygiene alone.
