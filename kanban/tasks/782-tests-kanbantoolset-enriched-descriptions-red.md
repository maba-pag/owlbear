---
id: 782
title: 'Tests: KanbanToolset enriched descriptions (RED)'
status: archived
priority: nice-to-have
created: 2026-03-13T15:03:23.8659428+01:00
updated: 2026-03-13T18:21:56.574097+01:00
started: 2026-03-13T15:03:32.1109934+01:00
completed: 2026-03-13T18:21:55.9323608+01:00
tags:
    - test
    - tooling
    - scope:core
class: standard
---

## Acceptance Criteria
- Add TestKanbanToolDescriptions class in tests/test_kanban_tools.py
- Follow pattern from TestFromAC_BrowserSnapshotDescription in tests/test_browser_toolset.py L736-770
- Test kanban_create description mentions each priority: someday, nice-to-have, important, needed, critical
- Test kanban_create description mentions default status: ideation
- Test kanban_move description mentions each status: ideation, backlog, todo, in-progress, review, docs, done
- Test kanban_edit description mentions editable fields: body, block, unblock, tags, priority, append_body
- Test kanban_list description mentions filters: status, tag, priority, blocked
- Test kanban_pick description mentions claim and move semantics
- All tests FAIL before enrichment (TDD RED phase)

## Architecture Notes
Introspect via ts.tools['tool_name'].description (FunctionToolset pattern).
Instantiate: KanbanToolset(kanban_dir=Path('/fake'), kanban_bin=Path('/fake/bin')).

[[2026-03-13]] Fri 15:47
## Test-Writer Notes
- Test file: tests/test_kanban_tools.py
- Classes: TestFromAC_KanbanToolDescriptions
- Tests per category: happy 25, edge 0, error 0, boundary 0
- Total: 25 tests, all FAIL
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| create mentions each priority | test_create_description_mentions_priority[5 params] | happy |
| create mentions default status | test_create_description_mentions_default_status_ideation | happy |
| move mentions each status | test_move_description_mentions_status[7 params] | happy |
| edit mentions editable fields | test_edit_description_mentions_field[6 params] | happy |
| list mentions filters | test_list_description_mentions_filter[4 params] | happy |
| pick mentions claim and move | test_pick_description_mentions_claim/move | happy |

[[2026-03-13]] Fri 16:32
## Builder Notes
- Files changed: src/owlbear/tools/kanban.py
- Tests: 84 passed (25 new description tests), coverage 100% on tools/kanban.py
- Lint: ruff clean
- Evidence: all 25 TestFromAC_KanbanToolDescriptions tests RED->GREEN
- Fixes applied: enriched description strings for kanban_create, kanban_move, kanban_edit, kanban_list, kanban_pick

[[2026-03-13]] Fri 16:58
## Review Evidence

### Test Results
- pytest: 84 passed, 0 failed (tests/test_kanban_tools.py)

### Lint Results
- ruff: All checks passed (src/owlbear/tools/kanban.py, tests/test_kanban_tools.py)

### Coverage
- src/owlbear/tools/kanban.py: 100%

### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | `in desc.lower()` substring match per keyword; descriptive error msgs |
| Negative/error paths | ADEQUATE | AC scope is description-content only; no negative paths required |
| Mutation reasoning | ADEQUATE | Each parametrized keyword independently caught; removing any keyword fails its case |
| Test independence | STRONG | Each test creates fresh KanbanToolset via `_desc()`; no shared state |
| Descriptive names | STRONG | e.g. `test_create_description_mentions_priority`, `test_pick_description_mentions_claim` |

### Security Review
- No security issues. Changes are string-only description enrichment. No user input, file I/O, subprocess changes, or new dependencies.

### Test Writer vs Builder Comparison
Builder did NOT modify TestFromAC_KanbanToolDescriptions. The class was added by the test-writer (line 829+) and appears identically in the builder's diff. All 25 test methods PRESERVED.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| Add TestKanbanToolDescriptions class | tests/test_kanban_tools.py L829 | TestFromAC_KanbanToolDescriptions (25 tests) | PASS |
| Follow pattern from TestFromAC_BrowserSnapshotDescription | Same `_desc()` helper + parametrize pattern | -- | PASS |
| create mentions each priority | kanban.py L115: `Priorities: someday, nice-to-have, important, needed, critical` | test_create_description_mentions_priority[5 params] | PASS |
| create mentions default status ideation | kanban.py L113: `Default status: ideation` | test_create_description_mentions_default_status_ideation | PASS |
| move mentions each status | kanban.py L121-122 | test_move_description_mentions_status[7 params] | PASS |
| edit mentions editable fields | kanban.py L128-129 | test_edit_description_mentions_field[6 params] | PASS |
| list mentions filters | kanban.py L97-98 | test_list_description_mentions_filter[4 params] | PASS |
| pick mentions claim and move | kanban.py L135: `claim and move` | test_pick_description_mentions_claim + _move | PASS |
| All tests FAIL before enrichment (TDD RED) | Test-writer notes confirm 25 RED; builder notes confirm RED->GREEN | -- | PASS |

### Verdict: PASS
Confidence: .94

### Action Taken
kanban edit 782 --status docs --release

[[2026-03-13]] Fri 17:37
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | String-only description enrichment on existing tools. KanbanToolset already in tech stack table (L58). No new behavior/API/conventions. |
| 2 | Docstrings complete | No | N/A | All 7 public methods already have accurate docstrings with Args sections. Changes were to description= params in add_function(), not docstrings. No new public API. |
| 3 | sources/overview.md | No | N/A | No external patterns used. |
| 4 | README.md | No | N/A | No CLI changes. |
| 5 | Research doc linked | No | N/A | No research phase. |
| 6 | No impact | Yes | Pass | Description-only enrichment with no docs implications. |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/782-* files found)

[[2026-03-13]] Fri 18:21
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| Add TestKanbanToolDescriptions class | test_kanban_tools.py L829: TestFromAC_KanbanToolDescriptions (25 tests) | PASS |
| Follow BrowserSnapshotDescription pattern | Same _desc() helper + parametrize pattern | PASS |
| create mentions each priority | 5 parametrized: someday, nice-to-have, important, needed, critical | PASS |
| create mentions default status ideation | test_create_description_mentions_default_status_ideation | PASS |
| move mentions each status | 7 parametrized: ideation, backlog, todo, in-progress, review, docs, done | PASS |
| edit mentions editable fields | 6 parametrized: body, block, unblock, tags, priority, append_body | PASS |
| list mentions filters | 4 parametrized: status, tag, priority, blocked | PASS |
| pick mentions claim and move | test_pick_description_mentions_claim + _move | PASS |
| All tests FAIL before enrichment (TDD RED) | Test-writer: 25 RED; Builder: RED->GREEN | PASS |

### Test Results
- pytest (scoped): 84 passed, 0 failed
- pytest (full): 3226 passed, 23 failed (all pre-existing: regex env 6, bootstrap line-count 1, chat_loop import 3, inter_doc_pipeline 8, role policies 4, httpx timeout 1)
- ruff: All checks passed

### Confidence: .97
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 2f96f5d | test | tests/test_kanban_tools.py | #782 |
| aa6c95b | feat | src/owlbear/tools/kanban.py | #782 |
