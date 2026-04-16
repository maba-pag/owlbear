---
id: 900
title: Update setup/init.py for .py hooks
status: research
priority: needed
created: 2026-04-16T22:54:19.247222+00:00
updated: 2026-04-16T22:54:19.247222+00:00
tags:
- phase-2
- scope:setup
- type:build
- platform
parent: 890
depends_on:
- 898
- 899
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] setup/init.py updated to copy .py hooks (not .ps1) from seed/.owlbear/hooks/
- [ ] All filename references changed from .ps1 to .py
- [ ] Hook seeding copies all 7 .py files to target project
- [ ] No .ps1 references remain in init.py
- [ ] grep ".ps1" setup/init.py returns no results
- [ ] All tests from #899 pass (GREEN)

## Files
- `setup/init.py` (edit)