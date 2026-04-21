---
id: 1057
title: 'C-12: GREEN — corruption detection & auto-fix'
status: todo
priority: needed
created: 2026-04-21T10:43:21.218408+00:00
updated: 2026-04-21T10:43:21.218408+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1048
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §4, §8.4
Module: `serve/kanban/src/owlbear_kanban/corruption.py`

## Acceptance Criteria

- [ ] AC-C17: 9 ERR_CORRUPT_* modes implemented with positive detection for each
- [ ] AC-C18: `detect_corruption(file_path, location)` returns `CorruptionError` for each mode
- [ ] AC-C21: Each code is a `CorruptionError` subclass per C8.8 shape (`code`, `user_message`, `file_path`)
- [ ] AC-C22: Auto-fix matrix (§4.2) implemented — per (mode, field, default) triple
- [ ] 9 modes: missing-frontmatter, duplicate-id, forbidden-field, id-mismatch, missing-required-field, invalid-field-type, status-out-of-range, duplicate-location, orphan-archive-ref
- [ ] All RED tests from C-03 (#1048) pass