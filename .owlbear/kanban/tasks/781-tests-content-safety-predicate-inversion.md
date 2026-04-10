---
id: 781
title: Tests — Content safety predicate inversion
status: backlog
priority: needed
created: '2026-04-10T12:30:43.995109+00:00'
updated: '2026-04-10T12:30:43.995109+00:00'
tags:
- phase-1
- scope:knowledge
- type:test
parent: 775
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `wrap_untrusted_content()` wraps content for source types: `url_list`, `authenticated_web`, and any unknown future type
- Tests verify `wrap_untrusted_content()` does NOT wrap content for `file`, `text`, `file_glob`
- Tests verify idempotency (no double-wrap) is preserved
- File: `tests/test_content_safety_inversion_775.py`

## Context
- WS-B: Pipeline Quality
- Scope item 8 from #775
- See research F4: defense-in-depth, safe to ship independently
