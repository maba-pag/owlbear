---
approved_at: '2026-07-14T20:58:52.533177+00:00'
categories: [domain-knowledge, pitfall]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-28T00:59:15.647721Z'
didnt_use_count: 6
id: 6b4ff7e4-2498-4128-9154-c4025b60252d
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.82
source_agent: builder
state: approved
title: Knowledge package enforces TYPE_CHECKING import hygiene
unremarkable_count: 0
updated_at: '2026-07-23T13:20:28.391673+00:00'
---

In serve/knowledge Python modules, ruff TC rules require type-only imports (e.g., CancelSignal, ContentFetcher, Callable) to be moved into TYPE_CHECKING blocks even with `from __future__ import annotations`.
