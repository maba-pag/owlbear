---
id: dc165239-d865-4f95-8089-62ad7b986305
title: Ruff RUF022 enforces sorted __all__ in protocols package
categories:
- pitfall
- tool-usage
confidence: 0.82
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-26T05:56:24.133222Z'
updated_at: '2026-05-26T08:37:49.985866Z'
approved_at: null
---

In owlbear-dev knowledge protocol modules, adding new exports to a large __all__ may trigger RUF022. Run ruff --fix/--unsafe-fixes or sort __all__ entries to keep lint green before quality-runner.
