---
id: 563
title: Add _SELECT_COLS constant to source_store.py
status: backlog
priority: someday
created: 2026-03-04T07:39:06.1335739+01:00
updated: 2026-03-07T04:26:04.7057558+01:00
started: 2026-03-07T04:26:04.7057558+01:00
tags:
    - audit
    - dry
    - knowledge
class: standard
---

DRY-11: SELECT column list inlined 6 times in source_store.py. BookmarkStore already uses _SELECT_COLS pattern. Follow same pattern.

Findings:
- File: src/owlbear/memory/knowledge/source_store.py
- 6 identical SELECT column lists at lines 93, 107, 120, 127, 140, 149
- Column list: id, name, source_type, config, scope, enabled, priority, last_refreshed_at, last_error, created_at, updated_at (11 cols)
- Prior art: BookmarkStore._SELECT_COLS in bookmark.py (class attr, string constant, used in f-string queries)
- INSERT at line 70 also lists columns but uses different formatting (parenthesized, with VALUES) - not a candidate for _SELECT_COLS
- _row_to_model already maps by positional index (row[0]..row[10]) - column order must stay stable

Approach:
1. Add _SELECT_COLS class attr (same pattern as BookmarkStore line 90)
2. Replace all 6 inline SELECTs with f-string referencing self._SELECT_COLS
3. Add noqa: S608 to f-string queries (same as BookmarkStore)
4. Existing tests should pass unchanged

AC:
1. _SELECT_COLS defined once as class attribute on KnowledgeSourceStore
2. All 6 SELECT queries reference _SELECT_COLS instead of inline column list
3. Column order unchanged (positional _row_to_model depends on it)
4. Existing tests pass unchanged
5. ruff clean
