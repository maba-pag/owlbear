---
id: d7dc3c6f-586d-45e3-a4e8-91109d5c6e7a
title: Pytest -k gate can fail on unrelated collection import errors
categories:
- pitfall
- tool-usage
confidence: 0.82
state: curated
scope_agents:
- builder
source_agent: builder
created_at: '2026-05-28T01:47:39.031644Z'
updated_at: '2026-05-28T03:39:29.243516Z'
approved_at: null
---

In builder proof gates that use pytest -k on tests/, unrelated test files with import-time errors still fail collection even if they don't match the -k expression. For task 1905 AC4, selector gate failed with ImportError in tests/test_mcp_kanban_newline_norm_1531.py (cannot import create_dr), making AC unreachable without extra ignores or prerequisite fix.
