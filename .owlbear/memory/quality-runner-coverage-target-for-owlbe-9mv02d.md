---
id: 6f106fd0-e22e-40fa-a680-de18fc4bf894
title: Quality-runner coverage target for owlbear_memory.engine
categories:
- tool-usage
- pitfall
confidence: 0.86
state: curated
scope_agents:
- builder
- verifier
source_agent: builder
created_at: '2026-05-25T03:30:08.998565Z'
updated_at: '2026-05-25T03:33:23.932928Z'
approved_at: null
---

For memory-engine tasks, coverage_modules='owlbear_memory.engine' works reliably; path-style coverage targets can report 0%, and mixed module selections may accidentally report owlbear_mcp_memory.engine. Use explicit module name plus memory-focused test_paths.
