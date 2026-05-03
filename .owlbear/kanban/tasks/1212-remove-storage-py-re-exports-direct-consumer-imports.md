---
id: 1212
title: Remove storage.py re-exports — direct consumer imports
status: backlog
priority: needed
created: 2026-04-30 15:29:15.222006+00:00
updated: 2026-05-03T19:37:52.631023+00:00
tags:
- audit-kanban
- architecture
parent:
depends_on:
- 1211
blocked: false
block_reason:
claimed_at: 2026-05-03T19:37:52.631023+00:00
archival_reason:
archival_refs: []
---

## Objective
Remove facade re-exports from storage.py; consumers import from source.

## Files
- storage.py (remove re-exports)
- All consumers importing parse_body/render_body/detect_corruption/repair_corruption/ActivityStore from storage

## Change
Remove facade re-exports from storage.py. Update consumers to import from source modules directly (body_parser, corruption, activity_store).

## AC
- [ ] storage.py no longer re-exports body_parser, corruption, activity_store symbols
- [ ] All consumer imports updated to source modules
- [ ] No ImportError at runtime
- [ ] Tests pass

## Finding: 3.3
