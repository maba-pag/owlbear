---
id: 1210
title: Break circular imports — extract leaf modules
status: backlog
priority: needed
created: '2026-04-30 15:29:06.259647+00:00'
updated: '2026-04-30 15:49:25.382019+00:00'
tags:
- audit-kanban
- architecture
parent:
depends_on:
- 1206
- 1209
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Break circular import risk by extracting leaf utilities to standalone modules.

## Files
- New: _duration.py, _locking.py
- engine.py, config_loader.py, storage.py (update imports)

## Change
Extract `_parse_duration()` + `_DURATION_RE` to `_duration.py`. Extract `_exclusive_file_lock()` to `_locking.py`. Update imports in engine.py, config_loader.py, storage.py.

## AC
- [ ] _duration.py exists with _parse_duration and _DURATION_RE
- [ ] _locking.py exists with _exclusive_file_lock
- [ ] No circular import paths
- [ ] All consumers use new import paths
- [ ] Tests pass

## Findings: 3.1 + 1.1

**AC note (from audit):** This task covers both finding 3.1 (circular imports) and finding 1.1 (triple duration parser). Must also eliminate the `models.py:_parse_claim_timeout` duplicate — the new `_duration.py` leaf module must be the single canonical parser imported by engine.py, models.py, and config_loader.py.