---
id: 509
title: 'Test: audit-centric dispatch-cycle trace ID'
status: archived
priority: medium
created: 2026-03-31 23:53:17.881707+02:00
updated: 2026-04-02 00:14:23.927106+02:00
started: 2026-04-02 00:14:13.139638+02:00
completed: 2026-04-02 00:14:13.139638+02:00
tags:
- scope:orchestrator
- phase-2
- test
class: standard
archival_reason: completed
archival_refs: []
---

## Context
TDD RED phase for #434. Write failing tests for cycle_id propagation in orchestrator audit models and dispatch loop.

## Acceptance Criteria
- [ ] Test DispatchEvent and CompletionEvent accept and serialize cycle_id field
- [ ] Test cycle_id defaults to empty string when not provided (backwards compat with legacy JSONL)
- [ ] Test dispatch_entry() propagates cycle_id to both DispatchEvent and CompletionEvent
- [ ] Test dispatch_wave() threads cycle_id through to dispatch_entry()
- [ ] Test AuditLog.query() filters by cycle_id when provided and returns all when cycle_id=None
- [ ] All tests fail before implementation (RED phase)

[[2026-04-01]] Wed 02:54
## Test-Writer Notes
- Test file: tests/test_dispatch_cycle_trace_id.py
- Classes: TestFromAC_CycleIdModels, TestFromAC_CycleIdSignatures, TestFromAC_CycleIdDispatchEntry, TestFromAC_CycleIdDispatchWave, TestFromAC_CycleIdRunLoop, TestFromAC_CycleIdAuditQuery
- Tests per category: happy 14, edge 8, error 4, boundary 6
- Total: 32 tests, all FAIL
- ruff: clean
- AC coverage: AC1=x6, AC2=x4, AC3=x7, AC4=x5, AC5=x8, AC6 verified 32/32 FAIL

[[2026-04-01]] Wed 15:45
## Builder Notes
- Files changed: audit/models.py, audit/log.py, orchestrator/loop.py
- Tests: 32 passed, coverage 100% on models.py
- Lint: ruff clean
- Evidence: 32/32 pass, uuid4 hex generation per cycle, cycle_id filter in AuditLog.query()
- Fixes applied: Added cycle_id: str = '' to DispatchEvent and CompletionEvent; cycle_id filter to AuditLog.query(); threaded cycle_id kwarg through dispatch_entry/_dispatch_sequential/_dispatch_parallel/dispatch_wave; uuid4().hex generated once per cycle in run_loop()

[[2026-04-01]] Wed 21:09
## Review Evidence
See docs/scratch/509-reviewer.md for full evidence.

[[2026-04-01]] Wed 21:09
## Review Evidence
See docs/scratch/509-reviewer.md for full evidence.

[[2026-04-01]] Wed 21:09
## Review Evidence
See docs/scratch/509-reviewer.md for full evidence.

[[2026-04-01]] Wed 23:19
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | .github/copilot-instructions.md | No | N/A | cycle_id is internal audit field; no user-facing behavior or API change |
| 2 | Docstrings | No | N/A | DispatchEvent and CompletionEvent have class docstrings; query() has 'filtered by optional parameters' which covers cycle_id; loop.py docstrings already mention cycle_id at lines 132 and 320 |
| 3 | docs/sources/overview.md | No | N/A | No external patterns used |
| 4 | README.md | No | N/A | No CLI changes |
| 5 | Research doc | No | N/A | No research phase for this task |

### Files Updated
- None

### Scratch Files Cleaned
- docs/scratch/509-reviewer.md (deleted)
