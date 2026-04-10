---
id: 749
title: 'P1-04: Remove voice I/O references from README and docs'
status: todo
priority: important
created: '2026-04-10T10:36:47.149977+00:00'
updated: '2026-04-10T10:36:47.149977+00:00'
tags:
- phase-1
- type:docs
- cleanup
- scope-reduction
parent: 745
depends_on:
- 747
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Context
Brief: see parent #745. Scratch tier — documentation edit.

The README.md directory layout table includes a `serve/voice/` row that must be removed after the code is deleted.

## Acceptance Criteria
1. `serve/voice/` row removed from the directory layout table in `README.md`
2. No other voice I/O references remain in `README.md`
3. `README-consumer.md` checked — remove any voice I/O references if present
4. CRITICAL: Do NOT touch ideation domain voice references (architect-voice, critic-voice, etc.) in any README

## Files
- Edit: `README.md`
- Check: `README-consumer.md`
