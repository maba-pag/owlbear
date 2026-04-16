---
id: 904
title: Delete .ps1 hook files from .owlbear/ and seed/
status: research
priority: needed
created: 2026-04-16T22:54:41.805109+00:00
updated: 2026-04-16T22:54:41.805109+00:00
tags:
- phase-3
- scope:hooks
- cleanup
- platform
parent: 890
depends_on:
- 897
- 898
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] All .ps1 files deleted from `.owlbear/hooks/` (7 files)
- [ ] All .ps1 files deleted from `seed/.owlbear/hooks/` (6 files)
- [ ] grep -r ".ps1" .owlbear/hooks/ returns no results
- [ ] grep -r ".ps1" seed/.owlbear/hooks/ returns no results
- [ ] No agent.md or init.py references to deleted .ps1 files remain (verified by prior tasks #897, #898, #900)
- [ ] Git commit records the deletion cleanly

## Files
- `.owlbear/hooks/*.ps1` (delete)
- `seed/.owlbear/hooks/*.ps1` (delete)