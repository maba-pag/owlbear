---
id: 902
title: Clean up legacy kanban-md.exe references
status: research
priority: important
created: 2026-04-16T22:54:41.784445+00:00
updated: 2026-04-16T22:54:41.784445+00:00
tags:
- phase-3
- cleanup
- platform
parent: 890
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] All references to `kanban-md.exe` in orchestrator source and test files identified
- [ ] References removed or guarded with proper platform skip conditions (pytest.mark.skipif)
- [ ] No bare .exe references remain in serve/orchestrator/ or tests/
- [ ] grep -r "kanban-md.exe" serve/ tests/ returns no results (or only guarded references)
- [ ] Existing tests still pass after cleanup

## Files
- `serve/orchestrator/` (edit, affected files)
- `tests/` (edit, affected test files)