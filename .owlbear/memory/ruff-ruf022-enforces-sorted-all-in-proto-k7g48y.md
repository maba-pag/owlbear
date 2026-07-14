---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-26T05:56:24.133222Z'
didnt_use_count: 0
id: dc165239-d865-4f95-8089-62ad7b986305
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: Ruff RUF022 enforces sorted __all__ in protocols package
unremarkable_count: 0
updated_at: '2026-07-14T22:46:36.524583+00:00'
---

In owlbear-dev knowledge protocol modules, adding new exports to a large __all__ may trigger RUF022. Run ruff --fix/--unsafe-fixes or sort __all__ entries to keep lint green before quality-runner.
