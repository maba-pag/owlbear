---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.88
contested_by_task: null
created_at: '2026-05-24T23:37:56.368408Z'
didnt_use_count: 0
id: df38ed95-dfce-44c2-b253-c06b65fce4a9
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: RUF022 __all__ sorting is case-sensitive
unremarkable_count: 0
updated_at: '2026-07-14T23:33:24.804686+00:00'
---

In this repo, Ruff RUF022 expects isort-style __all__ ordering with uppercase symbols before lowercase; e.g., "atomic_write" should be placed after capitalized exports like "WorkSession".
