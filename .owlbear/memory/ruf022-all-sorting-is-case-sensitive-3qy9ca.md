---
id: df38ed95-dfce-44c2-b253-c06b65fce4a9
title: RUF022 __all__ sorting is case-sensitive
categories:
- pitfall
- tool-usage
confidence: 0.88
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-24T23:37:56.368408Z'
updated_at: '2026-05-25T00:10:31.831401Z'
approved_at: null
---

In this repo, Ruff RUF022 expects isort-style __all__ ordering with uppercase symbols before lowercase; e.g., "atomic_write" should be placed after capitalized exports like "WorkSession".
