---
id: 899
title: 'Tests: setup/init.py .py hook seeding'
status: research
priority: needed
created: 2026-04-16T22:54:12.469696+00:00
updated: 2026-04-16T22:54:12.469696+00:00
tags:
- phase-2
- scope:setup
- type:test
- platform
parent: 890
depends_on:
- 894
- 895
- 896
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] Test file verifying setup/init.py seeds .py hooks (not .ps1) into target project
- [ ] Test verifying all 7 hook files are seeded
- [ ] Test verifying seeded settings.json does not contain Windows-only terminal profiles
- [ ] Test verifying no .ps1 filename references remain in init.py logic
- [ ] Tests fail (RED) — init.py still references .ps1

## Files
- `tests/test_init_py_hooks.py` (new, or extend existing init.py tests)