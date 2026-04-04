---
id: 586
title: 'Fix: add row-factory to mcp-memory app_lifespan'
status: in-progress
priority: needed
created: 2026-04-03T17:54:52.4003742+02:00
updated: 2026-04-04T03:08:32.2752254+02:00
tags:
    - scope:agents
    - phase-2
depends_on:
    - 525
    - 587
class: standard
---

Latent bug: server.py app_lifespan opens sqlite3.connect() without setting conn.row-factory = sqlite3.Row. list_entries (tools.py L224) and get_knowledge (tools.py L126) call dict(row) on cursor results, which requires row-factory. Without it, dict() on plain tuples raises ValueError. Tests mask this by setting row-factory in test helpers (test_memory_tools_556.py L91).

Discovered during #531 architecture review via challenger.

AC:
- [ ] server.py app_lifespan sets conn.row-factory = sqlite3.Row immediately after sqlite3.connect() (before PRAGMAs)
- [ ] get_knowledge and list_entries return correct list[dict] results when exercised through production lifespan (not test-helper connections)
- [ ] Existing tests continue to pass
- [ ] ruff clean

[[2026-04-03]] Fri 18:09
## Architecture Review
**Verdict:** APPROVE
**DR Verification:** N/A -- bug fix, not research-driven

### AC Assessment
| AC Line | Assessment | Action |
|---------|------------|--------|
| row-factory after connect | Precise, verifiable, correct location | Kept |
| get_knowledge/list_entries return list[dict] through production lifespan | Verifiable via #587 test task | Kept |
| Existing tests continue to pass | Standard regression | Kept |
| ruff clean | Standard lint gate | Added |

### Architecture Notes
One-liner fix in server.py app_lifespan. No interface changes, no cross-package impact. Only get_knowledge (tools.py L126) and list_entries (tools.py L224) use dict(row); set_approval_state and mark_for-deletion use tuple indexing (r[0]) and are unaffected. migrate.py uses its own connection with tuple indexing, also unaffected. Fix placement before PRAGMAs is correct (row-factory is independent of journal_mode/busy_timeout).

### Changes Made
- Refined AC: added placement specificity (before PRAGMAs), added ruff clean requirement
- Created test task #587 (Test: Fix row-factory in mcp-memory app_lifespan) at todo
- Added depends_on #587 to #586 for TDD compliance

### Dependencies
- Verified: #525 (Implement memory-mcp tools) at archived
- Added: #587 (test task, TDD RED phase) at todo

### Challenge Results
- Challenger: proceed
- Confidence in original: .82
- Key challenges: C1 (AC-2 test must exercise production lifespan not test helpers), C2 (lifecycle edge case, clean), C3 (error visibility for future maintainers)
- Architect response: C1 accepted -- already addressed in #587 AC line 2 (production lifespan path). C2 acknowledged, no action (verified no code re-assigns row-factory). C3 deferred as YAGNI -- defensive assertions are scope creep for a one-liner fix.

## Test-Writer Notes
- Test file: tests/test_row_factory_mcp_memory_587.py (written as part of #587 TDD RED task)
- Classes: TestFromAC_AppLifespanRowFactory
- Tests per category: happy 2, boundary 2
- Total: 4 tests, all PASS (fix already applied via #587 builder phase)
- ruff: clean (per #587 review evidence)

Pass-through: TDD RED phase completed via dedicated test task #587 (archived). All testable AC lines covered by tests/test_row_factory_mcp_memory_587.py. Fix applied in #587 builder phase.
