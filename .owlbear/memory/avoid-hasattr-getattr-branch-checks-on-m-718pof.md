---
id: f28fd5ef-56e5-43a8-8767-b0f8e9cdf078
title: Avoid hasattr/getattr branch checks on MagicMock contexts
categories:
- pitfall
- tool-usage
- domain-knowledge
confidence: 0.87
state: curated
scope_agents:
- builder
- test-writer
- reviewer
source_agent: builder
created_at: '2026-05-27T11:32:34.925889Z'
updated_at: '2026-05-27T11:54:06.840601Z'
approved_at: null
---

In MCP tool routing code, hasattr/getattr can falsely report optional attributes as present on MagicMock test contexts. For slot-safe optional attribute detection, use object.__getattribute__ with AttributeError guard so slotted dataclasses and legacy mock contexts route correctly.
