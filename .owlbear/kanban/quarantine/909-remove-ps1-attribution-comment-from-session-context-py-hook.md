---
id: 909
title: Remove .ps1 attribution comment from session-context.py hook
status: archived
priority: needed
created: 2026-04-17T10:47:30.435452+00:00
updated: 2026-04-17T10:48:45.120420+00:00
tags:
- phase-3
- scope:hooks
- cleanup
- platform
parent: 905
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Context

Task #905 AC6 requires `grep -r ".ps1" share/ seed/ setup/ .owlbear/hooks/` to return no results.

One hit remains: `.owlbear/hooks/session-context.py` line 4 contains "Python port of session-context.ps1 — bug-for-bug equivalent."

## Acceptance Criteria

- [ ] `.owlbear/hooks/session-context.py` docstring no longer references `.ps1`
- [ ] `grep -r ".ps1" share/ seed/ setup/ .owlbear/hooks/` returns no results
- [ ] Same change applied to `seed/.owlbear/hooks/session-context.py` if it exists
[[2026-04-17]]

## Completed

Fixed in commit af071875. All 3 ACs verified: no .ps1 in .owlbear/hooks/session-context.py, grep gate clean, seed copy was already clean (stripped by #898 builder).
