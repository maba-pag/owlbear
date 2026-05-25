---
id: a9168326-861d-49ca-98f2-c29f68fcf17e
title: BLE001 narrowing can conflict with injected RuntimeError tests
categories:
- pitfall
- domain-knowledge
- process
confidence: 0.84
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-25T07:28:09.072639Z'
updated_at: '2026-05-25T07:54:16.198429Z'
approved_at: null
---

When BLE001-driven narrowing removes broad catches, task-scoped tests may still inject RuntimeError to assert continuation semantics. Preserve narrow outer tuple and normalize injected RuntimeError at the call site (e.g., convert to ValueError) to satisfy both contracts without reintroducing broad catches.
