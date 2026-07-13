---
id: 586
title: 'Fix: add row-factory to mcp-memory app_lifespan'
status: archived
priority: medium
created: 2026-04-03 17:54:52.400374+02:00
updated: 2026-04-04 21:20:53.129987+02:00
started: 2026-04-04 21:20:53.129987+02:00
completed: 2026-04-04 21:20:53.129987+02:00
tags:
- scope:agents
- phase-2
depends_on:
- 525
- 587
class: standard
archival_reason: completed
archival_refs: []
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

[[2026-04-04]] Sat 19:06
## Builder Notes
- Files changed: none (fix and tests already applied in #587 builder phase)
- Pass-through: conn.row_factory = sqlite3.Row present at server.py (after sqlite3.connect(), before PRAGMAs)
- Tests: 4 passed (TestFromAC_AppLifespanRowFactory — test_row_factory_is_sqlite3_row, test_row_factory_is_not_none, test_get_knowledge_returns_list_of_dicts_via_production_lifespan, test_list_entries_returns_list_of_dicts_via_production_lifespan)
- Coverage: server.py 100% (verified in #587)
- Lint: ruff clean (packages/mcp-memory/ + test_row_factory_mcp_memory_587.py)
- Evidence: all AC lines satisfied — fix in place, production lifespan path exercised, existing tests unaffected

[[2026-04-04]] Sat 20:16
PASS #586 -> docs | confidence .97

## Review Evidence

**pytest:** `tests/test_row_factory_mcp_memory_587.py` — 4 passed in 0.86s (TestFromAC_AppLifespanRowFactory).
**Regression:** 134 mcp-memory tests passed (`-k "mcp_memory or memory_tools"`). The 19 failures visible in the `-k memory` run are pre-existing, unrelated tasks (#531 MCP transport, copilot settings, #568 tool access). None are regressions from this fix.
**ruff:** All checks passed (exit 0) on `packages/mcp-memory/` and `tests/test_row_factory_mcp_memory_587.py`.
**Coverage:** server.py 100%.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| server.py app_lifespan sets conn.row_factory = sqlite3.Row immediately after sqlite3.connect() (before PRAGMAs) | server.py L79-80: `conn = sqlite3.connect(...)` then `conn.row_factory = sqlite3.Row`; PRAGMA block starts at L83 | test_row_factory_is_sqlite3_row, test_row_factory_is_not_none | PASS |
| get_knowledge and list_entries return correct list[dict] via production lifespan | Tests use `async with app_lifespan(MagicMock()) as ctx:` directly; assert isinstance(results[0], dict), specific field values | test_get_knowledge_returns_list_of_dicts_via_production_lifespan, test_list_entries_returns_list_of_dicts_via_production_lifespan | PASS |
| Existing tests continue to pass | 134 mcp-memory scoped tests passed; 19 failures are pre-existing, unrelated to this fix | full suite | PASS |
| ruff clean | ruff exit 0, no output | — | PASS |

### TestFromAC Integrity (5.0)
No modifications detected. All 4 TestFromAC_AppLifespanRowFactory methods intact and strong.

### Test Quality (5.3)
**STRONG.** Assertions are specific: field-level checks (`results[0]["id"] == "entry-001"`). Production lifespan path exercised (not _make_conn). Mutation resistance: removing conn.row_factory = sqlite3.Row causes test_row_factory_is_sqlite3_row to fail (AssertionError) and dict tests to fail (ValueError). Tests are independent via tmp_path + monkeypatch. Names are descriptive.

test_row_factory_is_not_none is weaker (`is not None` vs `is sqlite3.Row`) but documented as a boundary check, redundant to the stronger test — ADEQUATE, not blocking.

### Security (5.1)
Clean. SQLite params are parameterized. No new deps. No secrets.

### Builder Process (5.7)
One ## Builder Notes section. Pass-through pattern (fix applied in #587 builder phase). No loop.

### 6.x Informational
approve.py also has `dict(row)` at L57 but uses its own `_open_conn()` which already sets row_factory — out of AC scope and correctly handled independently.

**Verdict: PASS | confidence .97**

[[2026-04-04]] Sat 20:25
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Bug fix only; no external interface or convention changed. copilot-instructions.md not affected. |
| 2 | Module docstrings | Yes | Verified | server.py app_lifespan docstring step (c) accurately documents conn.row_factory = sqlite3.Row. No edits needed. |
| 3 | External attribution | No | N/A | Bug discovered internally during #531 arch review; no external patterns used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | Arch review confirmed "not research-driven"; no docs/research file produced. |
| 6 | Scratch files | No | N/A | No docs/scratch/586-* files found. |

**Files updated:** None required.
**Scratch cleaned:** None existed.

[[2026-04-04]] Sat 21:20
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| server.py app_lifespan sets conn.row_factory = sqlite3.Row after connect, before PRAGMAs | server.py L80-81: conn = sqlite3.connect(...) then conn.row_factory = sqlite3.Row; PRAGMAs at L83 | PASS |
| get_knowledge and list_entries return list[dict] via production lifespan | test_get_knowledge_returns_list_of_dicts_via_production_lifespan, test_list_entries_returns_list_of_dicts_via_production_lifespan (both use app_lifespan directly) | PASS |
| Existing tests continue to pass | 135 mcp-memory scoped tests passed, 0 failures | PASS |
| ruff clean | ruff exit 0 on packages/mcp-memory/ and test file | PASS |

### Test Results
- pytest (task scope): 4/4 passed (test_row_factory_mcp_memory_587.py)
- pytest (memory scope): 135 passed, 0 failed
- pytest (full suite): 2827 passed, 384 failed, 1 error; all failures pre-existing (skill frontmatter, v2 infrastructure, voice, agents paths); 0 regressions in task scope
- ruff: all checks passed

### Architect Quality: 5/5
Specific location (after connect, before PRAGMAs), exact behavior (list[dict] via production lifespan), identified affected vs unaffected functions. Clean implementation path for a one-liner fix.

### Deduction Breakdown
- AC lines with no evidence: 0 (all 4 PASS)
- Lint violations: 0
- AC quality: 5 (no deduction)
- Missing reviewer evidence: not missing (detailed, PASS .97)
- Full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 51728e2 | test | tests/test_row_factory_mcp_memory_587.py | #587 |
| 72c41da | fix | packages/mcp-memory/.../server.py | #587 |
| 233a1dd | docs | packages/mcp-memory/.../server.py | #587 |
