---
approved_at: null
categories: [pitfall, domain-knowledge, process]
confidence: 0.84
contested_by_task: null
created_at: '2026-05-25T07:28:09.072639Z'
didnt_use_count: 0
id: a9168326-861d-49ca-98f2-c29f68fcf17e
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: BLE001 narrowing can conflict with injected RuntimeError tests
unremarkable_count: 0
updated_at: '2026-07-14T23:09:00.442610+00:00'
---

When BLE001-driven narrowing removes broad catches, task-scoped tests may still inject RuntimeError to assert continuation semantics. Preserve narrow outer tuple and normalize injected RuntimeError at the call site (e.g., convert to ValueError) to satisfy both contracts without reintroducing broad catches.
