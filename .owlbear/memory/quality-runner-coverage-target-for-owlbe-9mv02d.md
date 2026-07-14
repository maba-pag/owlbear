---
approved_at: null
categories: [tool-usage, pitfall]
confidence: 0.86
contested_by_task: null
created_at: '2026-05-25T03:30:08.998565Z'
didnt_use_count: 0
id: 6f106fd0-e22e-40fa-a680-de18fc4bf894
outstanding_count: 0
scope_agents: [builder, verifier]
score: 0.0
source_agent: builder
state: deleted
title: Quality-runner coverage target for owlbear_memory.engine
unremarkable_count: 0
updated_at: '2026-07-14T23:09:00.637863+00:00'
---

For memory-engine tasks, coverage_modules='owlbear_memory.engine' works reliably; path-style coverage targets can report 0%, and mixed module selections may accidentally report owlbear_mcp_memory.engine. Use explicit module name plus memory-focused test_paths.
