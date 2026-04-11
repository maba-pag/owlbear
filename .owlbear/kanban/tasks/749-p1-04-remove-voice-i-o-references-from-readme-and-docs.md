---
id: 749
title: 'P1-04: Remove voice I/O references from README and docs'
status: review
priority: important
created: '2026-04-10T10:36:47.149977+00:00'
updated: '2026-04-11T11:57:11.927132+00:00'
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

[[2026-04-11]]
## Builder Notes
- Non-impl pass-through — all AC already satisfied by #747 builder
- AC1: `serve/voice/` row absent from README.md (confirmed — zero matches for "serve/voice")
- AC2: No other voice I/O references in README.md (confirmed — zero matches for "voice")
- AC3: README-consumer.md has zero voice references (confirmed)
- AC4: Ideation domain voices untouched (only `share/agents/` and `share/skills/` contain those, never edited)
- No files changed
[[2026-04-11]]
Verification pass — all AC satisfied (already noted in Builder Notes above).