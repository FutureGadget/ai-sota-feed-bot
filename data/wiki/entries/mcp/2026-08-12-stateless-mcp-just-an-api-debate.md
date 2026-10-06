---
title: "Developers split on whether stateless MCP is just REST again"
date: 2026-08-12
theme: stateless-spec
evidence: [801edb72737f6642]
also: [tool-use]
---
The 2026-07-28 spec **removes the initialize handshake and session header** and adds required method and tool-name headers, so gateways can route agent traffic without parsing JSON. Some developers call this a rediscovery of REST; others say the shared standard was always the point.

The debate clarifies what MCP adds over a plain API call: the shared tool-description and discovery layer, not the stateful session the spec just dropped.
