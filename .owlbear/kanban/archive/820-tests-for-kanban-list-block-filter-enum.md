---
id: 820
title: Tests for kanban_list block_filter enum replacement
status: archived
priority: nice-to-have
created: 2026-03-15T08:04:22.1498787+01:00
updated: 2026-03-15T10:57:33.8988498+01:00
started: 2026-03-15T10:57:27.7077734+01:00
completed: 2026-03-15T10:57:27.7077734+01:00
tags:
    - test
    - tools
class: standard
---

Preceding test task for #534.

## Acceptance Criteria

- [ ] New test class `TestFromAC_BlockFilterEnum` in `tests/test_kanban_tools.py`:
  - `test_block_filter_blocked` -- `block_filter='blocked'` passes `--blocked` to CLI
  - `test_block_filter_not_blocked` -- `block_filter='not_blocked'` passes `--not-blocked` to CLI
  - `test_block_filter_unblocked` -- `block_filter='unblocked'` passes `--unblocked` to CLI
  - `test_block_filter_none_default` -- `block_filter=None` (default) adds no block-related flags
- [ ] Existing `TestKanbanList` tests for `blocked`, `not_blocked`, `unblocked` bools updated to use `block_filter` enum values
- [ ] All new/changed tests FAIL (RED) before implementation (ImportError or assertion error expected)
- [ ] ruff clean

## Files

- `tests/test_kanban_tools.py`

[[2026-03-15]] Sun 08:42
## Test-Writer Notes
- Test file: tests/test_kanban_tools.py
- Classes: TestFromAC_BlockFilterEnum (new), TestKanbanList (3 updated)
- Tests per category: happy 4, edge 0, error 0, boundary 3
- Total: 7 tests, all FAIL (TypeError: unexpected kwarg block_filter)
- ruff: clean
- AC coverage:

| AC Line | Test(s) | Category |
|---------|---------|----------|
| block_filter='blocked' passes --blocked | test_block_filter_blocked | happy |
| block_filter='not_blocked' passes --not-blocked | test_block_filter_not_blocked | happy |
| block_filter='unblocked' passes --unblocked | test_block_filter_unblocked | happy |
| block_filter=None adds no flags | test_block_filter_none_default | happy |
| Existing test_blocked_filter uses block_filter | test_blocked_filter | boundary |
| Existing test_not_blocked_filter uses block_filter | test_not_blocked_filter | boundary |
| Existing test_unblocked_filter uses block_filter | test_unblocked_filter | boundary |

[[2026-03-15]] Sun 09:05
## Builder Notes
- DUPLICATE of #817. Same AC, same test file, same implementation.
- Implementation committed under #817 (d1ed66a).
- No additional work needed.

[[2026-03-15]] Sun 09:06
## Builder Notes
- Pass-through: implementation already committed by upstream agent
- Files: src/owlbear/tools/kanban.py (block_filter param already present)
- Tests: 88 passed (7 block_filter-related), 0 failed
- Coverage: kanban.py 100% (109 stmts, 0 miss)
- Lint: ruff clean
- No code changes needed by builder

[[2026-03-15]] Sun 09:38
## Review Evidence

### Test Results
- pytest: 88 passed, 0 failed (tests/test_kanban_tools.py)
- block_filter tests: 4 TestFromAC + 3 updated TestKanbanList = 7 tests, all PASS

### Lint Results
- ruff: All checks passed (tests/test_kanban_tools.py, src/owlbear/tools/kanban.py)

### Coverage
- kanban.py: 100% (109 stmts, 0 miss)

### Pass 1 - CRITICAL
- Security: clean (create_subprocess_exec, no shell=True)
- Test integrity: all 4 TestFromAC tests PRESERVED (git diff 807f573 HEAD = empty)
- Test quality: STRONG assertion specificity, STRONG mutation reasoning, ADEQUATE neg paths, STRONG independence, STRONG names
- Data safety: no issues

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| block_filter=blocked passes --blocked | L250-259 | PASS |
| block_filter=not_blocked passes --not-blocked | L261-271 | PASS |
| block_filter=unblocked passes --unblocked | L273-283 | PASS |
| block_filter=None default no flags | L285-296 | PASS |
| Existing tests updated to block_filter | L187-209 | PASS |
| All FAIL RED before impl | Test-writer notes: TypeError | PASS |
| ruff clean | ruff check: All checks passed | PASS |

### Verdict: PASS (.95)

[[2026-03-15]] Sun 09:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only task, no behavior/API change |
| 2 | Docstrings complete | No | N/A | block_filter param already documented at kanban.py L163 |
| 3 | sources/overview.md | No | N/A | No external patterns adopted |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc linked | No | N/A | No research phase for this task |

### Files Updated
- None

### Scratch Files Cleaned
- None (no docs/scratch/820-* files found)

[[2026-03-15]] Sun 09:59
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | copilot-instructions.md | No | N/A | Test-only, no behavior change |
| 2 | Docstrings | No | N/A | block_filter documented at kanban.py L163 |
| 3 | sources/overview.md | No | N/A | No external patterns |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase |

### Files Updated
- None

### Scratch Files Cleaned
- None

[[2026-03-15]] Sun 09:59
## Docs Gate - No docs impact. Test-only task (block_filter enum tests). All 5 checks N/A.

[[2026-03-15]] Sun 10:57
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| TestFromAC_BlockFilterEnum class | test_kanban_tools.py L244: 4 methods | PASS |
| test_block_filter_blocked | L250: block_filter='blocked' -> --blocked asserted, others excluded | PASS |
| test_block_filter_not_blocked | L262: block_filter='not_blocked' -> --not-blocked asserted | PASS |
| test_block_filter_unblocked | L274: block_filter='unblocked' -> --unblocked asserted | PASS |
| test_block_filter_none_default | L286: no block flags asserted | PASS |
| Existing TestKanbanList updated | L181/L191/L201: 3 tests use block_filter= | PASS |
| All FAIL RED before impl | Test-writer: TypeError kwarg | PASS |
| ruff clean | All checks passed | PASS |

### Test Results
- pytest (scoped): 88 passed, 0 failed (test_kanban_tools.py)
- pytest (full): 3470 passed, 51 failed (all pre-existing: regex env, bootstrap sig, integration)
- ruff: All checks passed

### Upstream Commits
- d1ed66a feat: replace kanban_list boolean params with block_filter (#817, builder)
- 807f573 test: add failing tests for block_filter enum replacement (#820, test-writer)

### Confidence: .97
### Action: archive
