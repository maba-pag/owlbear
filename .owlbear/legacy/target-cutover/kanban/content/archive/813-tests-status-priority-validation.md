---
id: 813
title: Tests — status/priority validation
status: archived
priority: medium
created: '2026-04-10T21:21:54.982332+00:00'
updated: '2026-04-13T17:25:41.295200+00:00'
tags:
- phase-1
- type:test
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on: []
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- Tests verify `create_task` raises `ValueError` for invalid status
- Tests verify `create_task` raises `ValueError` for invalid priority
- Tests verify `edit_task` raises `ValueError` for invalid status
- Tests verify `edit_task` raises `ValueError` for invalid priority
- Tests verify valid status/priority values accepted (from config)
- Tests verify MCP adapter maps `ValueError` to `ToolError` for create_task and edit_task
- Tests fail RED before implementation

## Context

Phase 1, independent pair. No dependencies within Phase 1.
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/status-priority-validation-813.md
- Sources: 9 studied, 5 high-relevance (engine.py, server.py, config.yml, test_kanban_engine_crud.py, brief)
- Recommendation: Single test file with 14+ tests (3 classes), reuse existing fixture/assertion patterns (confidence: .95)
- Follow-up tasks created: none needed (#814 already exists as GREEN phase)
- Decision requests: none

## Validation Pass (2026-04-13)
Existing research doc found and validated. Current codebase state shows validation is already implemented in engine.py (create_task lines 318-324, edit_task lines 400-406) and MCP server.py (ValueError to ToolError mapping in both create_task and edit_task). All 16 tests in test_status_priority_validation_813.py pass GREEN. Research doc test design is accurate; "Current State" table is outdated but non-blocking. No additional follow-ups required.

## Challenge Results
- Challenger: SKIPPED — validation pass on existing complete research, trivial test task
- Confidence in original: .95
- Key challenges: none
- Researcher response: N/A
[[2026-04-13]]
## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| Tests verify `create_task` raises `ValueError` for invalid status | PASS — verifiable, covered by `test_create_task_invalid_status_raises_value_error` + near-miss variant | None |
| Tests verify `create_task` raises `ValueError` for invalid priority | PASS — verifiable, covered by `test_create_task_invalid_priority_raises_value_error` + capitalization variant | None |
| Tests verify `edit_task` raises `ValueError` for invalid status | PASS — verifiable, covered by `test_edit_task_invalid_status_raises_value_error` + near-miss variant | None |
| Tests verify `edit_task` raises `ValueError` for invalid priority | PASS — verifiable, covered by `test_edit_task_invalid_priority_raises_value_error` + near-miss variant | None |
| Tests verify valid status/priority values accepted (from config) | PASS — verifiable, boundary tests in both Create and Edit classes confirm valid values stored unchanged | None |
| Tests verify MCP adapter maps `ValueError` to `ToolError` | PASS — verifiable, 4 async tests mock engine exceptions and assert `ToolError` propagation | None |
| Tests fail RED before implementation | MOOT — implementation already exists in engine.py (create_task L318-324, edit_task L400-406) and server.py; tests pass GREEN. Non-blocking informational artifact. | Note only |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for status/priority validation — one concern |
| Interface clarity | PASS | All AC lines specify exact exception type, method, and condition |
| Dependency correctness | PASS | No dependencies declared or needed |
| Module layering | PASS | Tests import from `owlbear_kanban` (engine) and `owlbear_mcp_kanban` (server) — valid test→impl direction |
| TDD compliance | PASS | This IS the test task; #814 is its GREEN counterpart |
| KISS/YAGNI | PASS | 16 tests, 3 classes, minimal fixtures — no over-engineering |
| Premise challenge | PASS | Validation tests are needed to lock behavior before downstream changes |
| Pattern consistency | PASS | Uses `pytest.raises`, `tmp_path` fixtures, `MagicMock` for MCP context — matches existing `test_kanban_engine_crud.py` patterns |
| Security surface | N/A | Test-only task, no new system boundaries |
| Single domain | PASS | `scope:mcp-kanban` — kanban domain only |

### Architecture Notes
- Test file `tests/test_status_priority_validation_813.py` covers engine-level validation (ValueError) and MCP adapter mapping (ValueError→ToolError) in separate test classes — clean separation.
- Implementation already exists: engine.py validates against `config.statuses` and `config.priorities`; server.py catches `ValueError` in both `create_task` and `edit_task` handlers.
- The "fail RED" AC line is an artifact of TDD sequencing that was overtaken by events. All other 6 AC lines are independently verifiable.

### Challenge Results
- Challenger: FALLBACK — no challenger agent available in workspace
- Architect response: Proceeding — trivial test task with clear AC, existing tests verified, confidence .95

### Verdict: APPROVE
### Action Taken: Advanced #813 backlog → todo. All AC lines verifiable and specific. Pass-through tag `type:test` present.
[[2026-04-13]]
## Test-Writer Notes
- Test file: tests/test_status_priority_validation_813.py (already exists from prior pass)
- Classes: TestFromAC_CreateTaskValidation, TestFromAC_EditTaskValidation, TestFromAC_MCPAdapterValidation
- Total: 16 tests, **all PASS GREEN** — implementation was already present in engine.py (create_task L318-324, edit_task L400-406) and server.py before this task was claimed
- ruff: not re-checked (file unchanged)
- AC coverage: all 6 AC lines covered; "Tests fail RED" line is MOOT (per Architecture Review and Validation Pass in body)
- Pass-through per `type:test` tag — no new tests written; test file is a verified regression suite
[[2026-04-13]]
## Builder Notes
- Non-implementation task — `type:test` pass-through, no code changes needed.
- Test file: tests/test_status_priority_validation_813.py
- Test results: 16 passed, 0 failed (verified GREEN)
- Lint: not re-run (file unchanged per Test-Writer Notes)
- All 6 AC lines confirmed covered by existing tests; "fail RED" AC line is MOOT per Architecture Review.
[[2026-04-13]]
## Review Evidence

### Test Results
pytest: **16 passed, 0 failed** | ruff: **clean** | exit codes: pytest=0, ruff=0

### Coverage
| Module | % |
|--------|---|
| owlbear_kanban/engine.py | 40 |
| owlbear_mcp_kanban/server.py | 53 |
Expected low: tests exercise 2 specific validation paths inside large multi-method modules. No deduction.

### AC Compliance Table

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| create_task raises ValueError for invalid status | test_create_task_invalid_status_raises_value_error + near-miss variant | Yes — pytest.raises(ValueError) fails if exception not raised | COVERED |
| create_task raises ValueError for invalid priority | test_create_task_invalid_priority_raises_value_error + capitalization variant | Yes | COVERED |
| edit_task raises ValueError for invalid status | test_edit_task_invalid_status_raises_value_error + near-miss variant | Yes | COVERED |
| edit_task raises ValueError for invalid priority | test_edit_task_invalid_priority_raises_value_error + near-miss variant | Yes | COVERED |
| Valid status/priority values accepted (from config) | 4 boundary tests (in-progress/critical for create, done/someday for edit) | Yes — record.status/priority comparison fails if value mutated or rejected | COVERED |
| MCP adapter maps ValueError to ToolError | 4 async test_mcp_* tests with mock engine | Yes — pytest.raises(ToolError) fails if adapter doesn't catch ValueError | COVERED |
| Tests fail RED before implementation | MOOT — impl existed before task was claimed; accepted by arch review | N/A | MOOT |

### TestFromAC Integrity Check
No modifications detected. All 3 classes present, named correctly, each test has an explicit AC docstring. Assertion method (pytest.raises + field equality) is consistent with the pattern in test_kanban_engine_crud.py. All 16 assertions classified STRONG — none would pass with a broken implementation.

### Implementation Spot-Check (code-reader)
- engine.py create_task (L317-323): validates status against `{s["name"] for s in config.statuses}`; validates priority against `config.priorities`; raises ValueError with descriptive message. ✅
- engine.py edit_task (L400-406): same validation against cached config. ✅
- server.py create_task (L119-120): `except ValueError as exc: raise ToolError(str(exc)) from exc`. ✅
- server.py edit_task (L222-224): `except (FileNotFoundError, ValueError) as exc: raise ToolError(msg) from exc`. ✅

### Security
No concerns. No secrets, no injection surfaces, no path traversal. All fixtures use tmp_path isolation.

### Deductions
None.

### Confidence: .97
### Verdict: PASS → docs
[[2026-04-13]]
## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | No | N/A | `type:test` pass-through; no application logic created or modified |
| 2 | Module docstrings | No | N/A | No source `.py` files created or modified; test file only |
| 3 | External attribution → sources/overview.md | No | N/A | All 9 research sources are internal (engine.py, server.py, config.yml, test_kanban_engine_crud.py, brief.md) |
| 4 | CLI changes → README.md | No | N/A | No CLI changes |
| 5 | Research doc | Yes | PASS | `.owlbear/research/status-priority-validation-813.md` exists, linked from task body; follow-up noted as #814 (confirmed to exist, in `docs` status) |

**Files updated:** none

**Scratch files:** no `.owlbear/scratch/813-*` files found — nothing to clean

**No docs impact.** Task qualifies for direct advance.
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| create_task raises ValueError for invalid status | test_create_task_invalid_status_raises_value_error + near-miss variant (L109-116) | PASS |
| create_task raises ValueError for invalid priority | test_create_task_invalid_priority_raises_value_error + capitalization variant (L119-129) | PASS |
| edit_task raises ValueError for invalid status | test_edit_task_invalid_status_raises_value_error + near-miss variant (L157-168) | PASS |
| edit_task raises ValueError for invalid priority | test_edit_task_invalid_priority_raises_value_error + near-miss variant (L171-180) | PASS |
| Valid status/priority values accepted (from config) | Boundary tests in Create (L132-142) and Edit (L183-198) classes | PASS |
| MCP adapter maps ValueError to ToolError | 4 async tests (L228-270) with mock engine | PASS |
| Tests fail RED before implementation | MOOT: impl predated tests, accepted by architect | MOOT |

### Test Results
- pytest (task scope): 16 passed, 0 failed
- pytest (full suite): 347 failed, 4134 passed; no failures in task scope file
- ruff: All checks passed

### Commit Verification
- tests/test_status_priority_validation_813.py committed at 78a30c73 (test-writer)

### Architect Quality: 4/5
AC lines specific and verifiable. Minor artifact: "fail RED" AC line was overtaken by events but correctly handled as MOOT by all downstream agents. No builder improvisation needed.

### Deduction Breakdown
- No AC lines without evidence: 0
- Lint violations: 0
- AC quality 4/5 (above threshold): 0
- Reviewer evidence present and detailed: 0
- No full-suite failures in task scope: 0

### Confidence: 1.00
### Action: archive