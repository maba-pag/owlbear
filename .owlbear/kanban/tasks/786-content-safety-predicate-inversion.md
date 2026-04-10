---
id: 786
title: Content safety predicate inversion
status: backlog
priority: important
created: '2026-04-10T12:31:05.221180+00:00'
updated: '2026-04-10T12:31:05.221180+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 781
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `content_safety.py` predicate changed from `== "url"` to `not in ("file", "text", "file_glob")`
- All #781 tests pass; existing content_safety tests still pass
- Defense-in-depth: new source types are wrapped by default
- File: `serve/knowledge/src/owlbear_knowledge/content_safety.py`

## Context
- WS-B: Pipeline Quality
- Scope item 8 from #775
- See research F4: defense-in-depth, safe to ship independently
