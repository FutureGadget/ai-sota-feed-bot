---
title: "LangGraph CLI lets you declare compatible API version ranges"
date: 2026-06-21
theme: compatibility-signals
evidence: [473efa3d40555ca9]
---
`langgraph-cli` 0.4.30 added support for **compatible API version ranges**, so a project can state which substrate versions it is built against instead of implicitly accepting whatever is newest.

An implicit assumption becomes an explicit, checkable contract that CI can enforce.
