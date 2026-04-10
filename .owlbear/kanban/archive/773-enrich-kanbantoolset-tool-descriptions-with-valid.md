---
id: 773
title: Enrich KanbanToolset tool descriptions with valid statuses/priorities
status: archived
priority: nice-to-have
created: 2026-03-13T10:41:44.8745016+01:00
updated: 2026-03-13T19:56:52.0959864+01:00
started: 2026-03-13T14:13:33.432856+01:00
completed: 2026-03-13T19:56:43.7617669+01:00
tags:
    - tooling
    - scope:core
class: standard
---

depends_on: [782]

## Acceptance Criteria
- kanban_create description includes valid priorities (someday, nice-to-have, important, needed, critical) and default status (ideation)
- kanban_move description includes valid statuses (ideation, backlog, todo, in-progress, review, docs, done)
- kanban_edit description lists editable fields (body, block/unblock, tags, priority, append_body)
- kanban_list description mentions status, tag, priority, and blocked filters
- kanban_pick description mentions claim and move-to-status semantics
- kanban_show and kanban_context descriptions unchanged
- Pattern: multi-line description=(...) following browser_snapshot precedent in src/owlbear/tools/browser/toolset.py L178-186
- All existing tests pass (no behavioral change)
- New description tests from #782 pass

## References
- Research: docs/research/kanban-tool-descriptions.md
- Precedent: src/owlbear/tools/browser/toolset.py L178-186 (browser_snapshot)
- Precedent: src/owlbear/tools/knowledge_source.py L74-97 (KnowledgeSourceToolset)
- Source file: src/owlbear/tools/kanban.py _register_tools() L92-131
- Test file: tests/test_kanban_tools.py TestToolRegistration class

[[2026-03-13]] Fri 15:04
## Architecture Review
**Verdict:** APPROVED

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| kanban_create: priorities + default status | Specific values listed, verifiable | Kept |
| kanban_move: valid statuses | Full pipeline listed, verifiable | Kept |
| kanban_edit: editable fields | Field list matches method signature | Kept |
| kanban_list: mention filters | Refined from vague to specific filter names | Refined |
| kanban_pick: claim/move semantics | Clear and verifiable | Kept |
| kanban_show/context unchanged | Correct, no enum params | Kept |
| Pattern: browser_snapshot precedent | Multi-line description=() | Added |
| Existing tests pass | Regression guard | Kept |
| #782 description tests pass | TDD compliance | Added |

### Architecture Notes
- Single file change: src/owlbear/tools/kanban.py _register_tools() L92-131
- Pattern: multi-line description=() per browser_snapshot (toolset.py L178-186)
- Introspection: ts.tools['name'].description (FunctionToolset stores Tool objects)
- No new deps, no interface changes, no behavioral changes
- Config values from kanban/config.yml are stable since inception

### Changes Made
- Created #782 (test task, TDD RED) at todo
- Refined AC: made filter line explicit, added pattern/precedent references
- Added depends_on: [782] in body

### Dependencies
- Added: #782 (Tests: KanbanToolset enriched descriptions)  preceding test task
- Verified: no other dependencies needed (standalone string edits)

[[2026-03-13]] Fri 18:13
## Test-Writer Notes
- Test file: tests/test_kanban_tools.py (pre-written under #782)
- Classes: TestFromAC_KanbanToolDescriptions
- Tests: 25 total (happy 25, edge 0, error 0, boundary 0)
- Note: Architect split #782 as TDD RED for #773. All 25 tests verified present.
- Uncovered AC lines (show/context unchanged, multi-line pattern, existing tests pass) are regression/style constraints — no new behavior to test.

[[2026-03-13]] Fri 18:32
## Builder Notes
- Files changed: none (implementation already completed under #782)
- Tests: 84 passed (25 description tests + 59 existing), coverage 100% on tools/kanban.py
- Lint: ruff clean
- Evidence: all 25 TestFromAC_KanbanToolDescriptions tests already GREEN from #782 builder work
- Fixes applied: None -- code already satisfies all AC

[[2026-03-13]] Fri 19:56
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| kanban_create: priorities + default status | kanban.py L115-120: all 5 priorities + ideation default | PASS |
| kanban_move: valid statuses | kanban.py L122-127: all 7 pipeline statuses listed | PASS |
| kanban_edit: editable fields | kanban.py L129-134: body, block, unblock, tags, priority, append_body | PASS |
| kanban_list: filters | kanban.py L95-101: status, tag, priority, blocked | PASS |
| kanban_pick: claim + move semantics | kanban.py L136-141: claim and move options | PASS |
| show/context unchanged | kanban.py L103-106, L143-146: simple single-line, no enrichment | PASS |
| Multi-line description=() | All 5 enriched tools use parenthesized strings | PASS |
| Existing tests pass | 84/84 in test_kanban_tools.py | PASS |
| #782 description tests pass | 25 TestFromAC_KanbanToolDescriptions GREEN | PASS |

### Test Results
- pytest scoped: 84 passed, 0 failed
- pytest full: partial (258-464 passed, 0 failures) before env KeyboardInterrupt
- ruff: clean

### Confidence: .97
### Action: archive

Note: Code committed under #782 (aa6c95b, 2f96f5d). No new commits for #773.
