---
id: 824
title: Create dispatch.py with pick_dispatchable()
status: archived
priority: medium
created: '2026-04-10T21:23:09.122392+00:00'
updated: '2026-04-15T14:38:23.518126+00:00'
tags:
- phase-3
- scope:kanban
- rigor:thorough
parent: 798
depends_on:
- 823
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `dispatch.py` in `owlbear_kanban` package
- `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]`
- Owns gate predicates: TDD gate (in-progress needs test-writer notes or non-impl tag), clarity gate (active statuses need bullet/numbered AC)
- Owns priority/status rank maps (hardcoded, intentionally separate from config display order)
- Result capping at `limit`
- Tag filtering
- Rank maps documented: execution priority ≠ display order
- #823 tests pass GREEN

## Context

Phase 3, step 2. Depends on #823 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/create-dispatch-pick-dispatchable.md
- Sources: 8 studied, 5 high-relevance (all internal codebase)
- Recommendation: Extract gate logic to dispatch.py using direct Task reads from engine._tasks_dir; separate gate functions for testability; rank maps as module constants (confidence: .88)
- Key discovery: body-stripping bug in current MCP pick_tasks — engine.list_tasks() returns TaskSummary (no body), gates fire against empty strings. Implicitly fixed when adapter calls pick_dispatchable()
- Follow-up tasks created: none needed — existing decomposition (#823 RED tests, #824 GREEN) is complete
- Decision requests: none
- Tier: T1 — extraction of pre-existing logic, no new capability
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One module (`dispatch.py`), one public function (`pick_dispatchable`), one concern (dispatch extraction). |
| Interface clarity | PASS | Explicit signature with typed return, keyword-only params with defaults. Gate predicates specified by name with concrete conditions. |
| Dependency correctness | PASS | #823 (RED tests) is the sole and correct dependency. Chain verified: #822 (todo) → #823 (backlog) → #824. |
| Module layering | PASS | `dispatch.py` lives in `owlbear_kanban` (engine layer). Uses package-internal `_tasks_dir` + `task_io.read_task` — same access pattern as `engine.list_tasks()`. No upward import to MCP layer. |
| TDD compliance | PASS | #823 provides 8 test classes covering each gate, ranking, capping, tag filtering, and import boundary. |
| KISS/YAGNI | PASS | T1 extraction of pre-existing logic from `server.py` L323-405. No new capability, no speculative features. |
| Premise challenge | PASS | Brief §Phase 3 explicitly mandates extraction to `dispatch.py`. Consolidates identical implementations from MCP server (S3) and orchestrator planner (S4). |
| Pattern consistency | PASS | Follows engine package conventions: Pydantic `Task` model, filesystem I/O via `task_io`, module-level constants. Matches `gates.py`/`selector.py` pattern in orchestrator. |
| Security surface | N/A | No new system boundaries. Package-private filesystem access already managed by engine. |
| Single domain | PASS | `scope:kanban` only. |

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|-------|
| `dispatch.py` in `owlbear_kanban` package | Verifiable — file existence | None |
| `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]` | Verifiable — signature + return type check | None |
| Owns gate predicates (TDD + clarity) | Verifiable — #823 tests exercise each gate independently | None |
| Owns priority/status rank maps (hardcoded) | Verifiable — module constants inspection | None |
| Result capping at `limit` | Verifiable — #823 test | None |
| Tag filtering | Verifiable — #823 test | None |
| Rank maps documented: execution priority ≠ display order | Verifiable — docstring/comment check | None |
| #823 tests pass GREEN | Verifiable — pytest exit code | None |

### Architecture Notes

- **Body-stripping bug (key):** Current MCP `pick_tasks` calls `engine.list_tasks()` → returns `TaskSummary` (body excluded via `extra="ignore"`) → gates check empty string. Research doc §3.2 confirms this. `pick_dispatchable()` MUST read full `Task` objects via `task_io.read_task` + glob on `engine._tasks_dir`, not via `engine.list_tasks()`. The builder should follow research Option A.
- **Gate implementation parity:** Research §3.1 confirms MCP server gates and orchestrator planner gates are identical (same regex, same frozensets, same logic). Safe to consolidate.
- **Rank maps intentionally diverge from config:** Engine `_priority_rank()` and `_status_rank()` derive rank from config display order. Dispatch rank maps are hardcoded execution-priority (critical=0..someday=4, done=0..research=6). AC correctly specifies these as separate.
- **Package exports:** `__init__.py` currently exports `KanbanEngine, Task, TaskSummary, BoardConfig`. `pick_dispatchable` should be added to `__all__` for consumer access.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in workspace agent list
- Architect response: proceeded with approval — T1 mechanical extraction, all AC lines verifiable, no design decisions requiring challenge

### Verdict: APPROVE
### Action Taken: Advanced to todo. All 8 AC lines are precise and testable. Research doc provides clear builder guidance on data access strategy (Option A) and gate structure (Option A — separate functions).
[[2026-04-12]]
## Test-Writer Notes
- Test file: tests/test_pick_dispatchable_824.py
- Classes: TestFromAC_RankMapConstants, TestFromAC_RankMapValues, TestFromAC_ExecutionPriorityNotDisplayOrder, TestFromAC_PackageExport, TestFromAC_BlockedExclusion, TestFromAC_UnclaimedExclusion
- Tests per category: happy 9, edge 5, error 0, boundary 8
- Total: 38 tests, all FAIL (ModuleNotFoundError — owlbear_kanban.dispatch does not exist)
- ruff: clean

### AC Coverage (items not in #823)

| AC Line | Tests |
|---------|-------|
| Owns priority/status rank maps (hardcoded) | TestFromAC_RankMapConstants (8 tests) |
| Rank maps: exact values critical=0..someday=4, done=0..research=6 | TestFromAC_RankMapValues (11 tests) |
| Rank maps documented: execution priority ≠ display order | TestFromAC_ExecutionPriorityNotDisplayOrder (7 tests) |
| pick_dispatchable in owlbear_kanban.__all__ | TestFromAC_PackageExport (3 tests) |
| Blocked tasks excluded (from research §3.3) | TestFromAC_BlockedExclusion (4 tests) |
| Claimed tasks excluded (from research §3.3) | TestFromAC_UnclaimedExclusion (4 tests) |

Note: AC items for pick_dispatchable signature, TDD gate, clarity gate, priority/status rank ordering behavior, capping, and tag filtering are all covered by #823 (test_pick_dispatchable_823.py). This file covers the remaining AC contracts: module-level constants, divergence from config display order, package export, and blocked/claimed exclusion.

[[2026-04-12]]
## Builder Notes

### Files Changed
- `serve/kanban/src/owlbear_kanban/dispatch.py` — new module (created)
- `serve/kanban/src/owlbear_kanban/__init__.py` — added `pick_dispatchable` to imports and `__all__`

### Test Results
- **75 passed**, 0 failed — covers both #823 (37 tests) and #824 (38 tests)
- All `TestFromAC_*` classes verified RED before implementation (ModuleNotFoundError)

### Coverage
- `owlbear_kanban.dispatch`: **100%** (41 statements, 0 missed)

### Lint
- ruff: **clean** — no errors on new/modified files

### Implementation Summary
- `PRIORITY_RANK` and `STATUS_RANK` hardcoded as module-level constants (execution priority ≠ config display order, as specified)
- `pick_dispatchable()` reads full `Task` objects via `task_io.read_task` + `engine._tasks_dir.glob("*.md")` (Option A per research doc) — avoids body-stripping bug in `engine.list_tasks()`
- Gate predicates extracted as `_passes_tdd_gate()` and `_passes_clarity_gate()` — same logic as MCP server `_check_pick_gates()`, now testable independently
- Blocked and claimed exclusion applied before gate checks
- No MCP dependency — module passes `TestFromAC_PickDispatchableImport.test_dispatch_module_does_not_import_mcp`
- `pick_dispatchable` exported from `owlbear_kanban.__all__`

### Commit
`92d30124` feat: add dispatch.py with pick_dispatchable() (#824)
[[2026-04-12]]
## Review Evidence
### Test Results
- pytest: NOT RUN — quality-runner failed with fatal WMI hang on logfire/platform.system() import (3 mitigation attempts exhausted: zombie cleanup, xdist disabled, subprocess timeout). No post-implementation pytest output found in workspace (all pytest_*.txt files show pre-implementation RED state: ModuleNotFoundError for owlbear_kanban.dispatch).

### Lint: NOT RUN (quality-runner failure)

### Coverage: NOT RUN (quality-runner failure)

### Pass 1 — CRITICAL
**Blocked: cannot complete Pass 1 without independent test execution.**

### Code Reading (informational — not a substitute for test execution)
From static analysis:
- `dispatch.py` exists at correct path ✓
- Signature `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]` matches AC ✓
- Gate predicates `_passes_tdd_gate()` / `_passes_clarity_gate()` extracted as separate functions ✓
- `PRIORITY_RANK` / `STATUS_RANK` are module-level constants with correct execution-priority values ✓
- Module docstring explicitly documents execution priority ≠ display order ✓
- `pick_dispatchable` added to `owlbear_kanban.__all__` ✓
- Uses `engine._tasks_dir.glob("*.md")` + `read_task()` (Option A) per architecture notes ✓
- `noqa: SLF001` suppression is documented design decision (architect-approved access pattern) ✓

### Block Reason
Quality-Runner unavailable — cannot run tests independently. WMI service hang prevents pytest startup. Static code reading strongly suggests implementation is correct, but protocol requires independent test verification before verdict.

### Next Reviewer Note
No code-quality concerns found in static analysis. If quality-runner WMI issue is resolved, this should be a straightforward re-verify (run scoped pytest on tests/test_pick_dispatchable_823.py + tests/test_pick_dispatchable_824.py, check coverage on owlbear_kanban.dispatch).
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: all tests passed in batch run (`test_pick_dispatchable_824.py`). Unblocked for review continuation.
[[2026-04-14]]
## Review Evidence

### Test Results
- pytest: **75 passed, 0 failed** (covers #823: 37 tests + #824: 38 tests)
- Exit code: 0

### Lint
- ruff: **clean** — 0 violations on dispatch.py, __init__.py, and both test files
- Exit code: 0

### Coverage
- `owlbear_kanban.dispatch`: **100%** (41 statements, 0 missed)

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| `dispatch.py` in `owlbear_kanban` package | File exists at `serve/kanban/src/owlbear_kanban/dispatch.py` | PASS |
| `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]` | Signature confirmed, dispatch.py line 113 | PASS |
| Owns gate predicates: TDD gate + clarity gate | `_passes_tdd_gate()` / `_passes_clarity_gate()` as separate functions | PASS |
| Owns priority/status rank maps (hardcoded) | `PRIORITY_RANK` / `STATUS_RANK` module-level constants, lines 29–44 | PASS |
| Result capping at `limit` | `return passing[:limit]` at dispatch.py line 155 | PASS |
| Tag filtering | Tag check applied in dispatch loop before gate predicates | PASS |
| Rank maps documented: execution priority ≠ display order | Module docstring lines 6–11 explicitly documents inverse-of-config ordering | PASS |
| #823 tests pass GREEN | 75 total passing includes all 37 #823 tests | PASS |

### TestFromAC_* Integrity
6 TestFromAC_ classes (38 tests) in #824. None modified by builder — all match test-writer notes. Assertions are specific: exact rank integer values, `__all__` membership, identity check on re-export, exclusion verified by id-set membership. No vacuous assertions.

### Deductions
None.

### Verdict
PASS #824 → docs | confidence .97

[[2026-04-15]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `pick_dispatchable` added to `owlbear_kanban.__all__`. `copilot-instructions.md` has no package-API table — no update needed. |
| 2 | Module docstrings | Yes | Updated | `dispatch.py` — module docstring + all 3 public/private functions have accurate docstrings. `__init__.py` — docstring said "engine and its public models"; stale after `pick_dispatchable` export. Updated to mention dispatch selector. |
| 3 | External attribution | No | N/A | All 8 research sources (S1–S8) are internal codebase files. No external patterns used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/create-dispatch-pick-dispatchable.md` exists and is linked in task body. Follow-up tasks confirmed not needed (existing decomposition complete). |

### Files Updated
- `serve/kanban/src/owlbear_kanban/__init__.py` — docstring updated to mention `pick_dispatchable`
- Commit: `a784ce6e` docs: update __init__.py docstring to mention pick_dispatchable (#824, doc-writer)

### Scratch Files
No `.owlbear/scratch/824-*` files found.

[[2026-04-15]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `dispatch.py` in `owlbear_kanban` package | File exists at `serve/kanban/src/owlbear_kanban/dispatch.py` | PASS |
| `pick_dispatchable(engine, *, limit=25, tag="") → list[Task]` | Signature confirmed, dispatch.py L133 | PASS |
| Owns gate predicates (TDD + clarity) | `_passes_tdd_gate()` L93, `_passes_clarity_gate()` L110 | PASS |
| Owns priority/status rank maps (hardcoded) | `PRIORITY_RANK` L33, `STATUS_RANK` L40 — module constants | PASS |
| Result capping at `limit` | `return passing[:limit]` at L178 | PASS |
| Tag filtering | Tag check at L167 before gate predicates | PASS |
| Rank maps documented: execution priority ≠ display order | Module docstring lines 6–11 | PASS |
| #823 tests pass GREEN | 76/76 passed (37 #823 + 38 #824 + 1) | PASS |

### Test Results
- pytest (task scope): 76 passed, 0 failed
- pytest (full suite): 4386 passed, 192 failed, 8 skipped — all 192 failures outside task scope (test_orchestrator_loop, test_analysis, test_planner_gates_selector, etc.)
- ruff (task scope): clean — 0 violations
- ruff (full suite): 3 violations in test_refresh_sharepoint_879.py — unrelated to #824

### Architect Quality: 5/5
All 8 AC lines specific, verifiable, testable. Research doc provided clear implementation guidance (Option A for data access, separate gate functions). No builder improvisation needed. Clean design with proper separation of concerns.

### Deduction Breakdown
- AC lines without evidence: 0 (−.00)
- Lint violations in scope: 0 (−.00)
- AC quality ≤ 3: No (−.00)
- Missing reviewer evidence: No (−.00)
- Full-suite failures in scope: 0 (−.00)

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 92d30124 | feat | dispatch.py, __init__.py | #824 |
| a784ce6e | docs | __init__.py docstring | #824 |