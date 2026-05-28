---
id: 6b4ff7e4-2498-4128-9154-c4025b60252d
title: Knowledge package enforces TYPE_CHECKING import hygiene
categories:
- domain-knowledge
- pitfall
confidence: 0.82
state: curated
scope_agents:
- builder
- reviewer
source_agent: builder
created_at: '2026-05-28T00:59:15.647721Z'
updated_at: '2026-05-28T01:31:47.089527Z'
approved_at: null
---

In serve/knowledge Python modules, ruff TC rules require type-only imports (e.g., CancelSignal, ContentFetcher, Callable) to be moved into TYPE_CHECKING blocks even with `from __future__ import annotations`.
