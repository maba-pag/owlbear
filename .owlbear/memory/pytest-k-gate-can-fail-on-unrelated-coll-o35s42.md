---
approved_at: null
categories: [pitfall, tool-usage]
confidence: 0.82
contested_by_task: null
created_at: '2026-05-28T01:47:39.031644Z'
didnt_use_count: 0
id: d7dc3c6f-586d-45e3-a4e8-91109d5c6e7a
outstanding_count: 0
scope_agents: [builder]
score: 0.0
source_agent: builder
state: deleted
title: Pytest -k gate can fail on unrelated collection import errors
unremarkable_count: 0
updated_at: '2026-07-14T20:22:49.873860+00:00'
---

In builder proof gates that use pytest -k on tests/, unrelated test files with import-time errors still fail collection even if they don't match the -k expression. For task 1905 AC4, selector gate failed with ImportError in tests/test_mcp_kanban_newline_norm_1531.py (cannot import create_dr), making AC unreachable without extra ignores or prerequisite fix.
