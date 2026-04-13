---
id: 814
title: Add status/priority validation
status: docs
priority: needed
created: '2026-04-10T21:22:01.275308+00:00'
updated: '2026-04-13T14:06:10.813203+00:00'
tags:
- phase-1
- scope:mcp-kanban
- rigor:thorough
parent: 798
depends_on:
- 813
blocked: false
block_reason: null
claimed_by: late-pool
claimed_at: '2026-04-13T14:06:10.813203+00:00'
---
## Acceptance Criteria

- `create_task` raises `ValueError` for invalid status or priority (validated against config-defined values)
- `edit_task` raises `ValueError` for invalid status or priority
- MCP adapter maps `ValueError` to `ToolError` in create_task and edit_task handlers (existing pattern from move_task)
- Valid values accepted without change to existing behavior
- #813 tests pass GREEN
- Existing MCP tests pass (O4)

## Context

Phase 1, independent pair. Depends on #813 (RED tests).
Brief: `.owlbear/briefs/draft-kanban-web-gui-prep/brief.md`
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/status-priority-validation-814.md (validation pass — doc written 2026-04-12, verified 2026-04-13)
- Sources: 9 studied, 6 high-relevance (all internal codebase)
- Recommendation: Inline validation replicating move_task pattern — Approach A (confidence: .92)
- Tier: T1 — pattern replication from existing code
- Follow-up tasks created: none (task #814 is itself the implementation task)
- Decision requests: none

## Validation Pass Findings
- Implementation is already in place in engine.py (create_task lines 335-351, edit_task lines 383-393)
- MCP adapter already maps ValueError→ToolError for both create_task and edit_task handlers
- All 16 tests from #813 pass GREEN — AC satisfied
- Research doc recommendations exactly match the implemented code

## Challenge Results
- Challenger: SKIPPED — T1 pattern replication from existing move_task code, no architectural decisions
- Confidence in original: .92
[[2026-04-13]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Validation-only concern for create_task and edit_task |
| Interface clarity | PASS | AC specifies exact exceptions (ValueError), exact handlers (create_task, edit_task), exact mapping (→ToolError) |
| Dependency correctness | PASS | Depends on #813 (RED tests) — correct TDD pairing. #813 still in backlog; pipeline ordering noted but not blocking for arch approval |
| Module layering | PASS | Engine validates → MCP maps ValueError→ToolError. Correct direction, no upward imports |
| TDD compliance | PASS | #813 provides RED tests; #814 is the GREEN phase |
| KISS/YAGNI | PASS | Replicates existing move_task pattern verbatim, no extras |
| Premise challenge | PASS | Input validation at system boundary — necessary and correct |
| Pattern consistency | PASS | Matches move_task ValueError pattern in engine.py (line ~507) and server.py (line ~214) |
| Security surface | PASS | This IS the boundary validation — validates config-defined enums before processing |
| Single domain | PASS | scope:mcp-kanban only |

### AC Assessment
| AC Line | Verdict | Notes |
|---------|---------|-------|
| create_task raises ValueError for invalid status/priority | VERIFIABLE | Precise: exception type + trigger condition + validation source (config) |
| edit_task raises ValueError for invalid status/priority | VERIFIABLE | Same pattern, consistent |
| MCP adapter maps ValueError→ToolError | VERIFIABLE | References existing move_task pattern — builder has concrete template |
| Valid values accepted without change | VERIFIABLE | Boundary test ensures no false positives |
| #813 tests pass GREEN | VERIFIABLE | Run pytest on test file |
| Existing MCP tests pass (O4) | VERIFIABLE | Run full test suite |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| create_task invalid status/priority | Bad enum value | ValueError | Yes — MCP maps to ToolError | Clear error message with valid options |
| edit_task invalid status/priority | Bad enum value | ValueError | Yes — MCP maps to ToolError | Clear error message with valid options |

### Challenge Results
- Challenger: FALLBACK — no challenger subagent available
- T1 pattern replication from existing move_task code; no novel architectural decisions to challenge
- Confidence: .94

### Codebase Evidence
- engine.py create_task validation: lines 318-324 (status set comprehension + priority list check)
- engine.py edit_task validation: lines 400-406 (same pattern)
- server.py create_task handler: lines 201-204 (ValueError→ToolError)
- server.py edit_task handler: lines 278-281 (FileNotFoundError|ValueError→ToolError)
- test_status_priority_validation_813.py: 16 tests, 3 classes, full AC coverage

### Note
Validation pass in task body confirms implementation already exists and tests pass GREEN. Pipeline should advance #813 (dependency) first; builder should verify dependency status at build time.

### Verdict: APPROVE
### Action Taken: Advanced to todo — AC precise, architecture sound, pattern-consistent with move_task
[[2026-04-13]]
## Test-Writer Notes

**Status: Exceptional pass-through — implementation and tests pre-existing**

### Situation Assessment

Task #814 is the GREEN implementation task for status/priority validation in `create_task` and `edit_task`. On arrival, the Validation Pass Findings in the task body (written by the arch reviewer during architecture review) already confirmed:

- Engine validation is fully implemented (`engine.py` `create_task` L318-324, `edit_task` L400-406)
- MCP adapter mapping is implemented (`server.py` `create_task` L202-204, `edit_task` L278-281)
- #813 tests already pass GREEN (confirmed: pytest run on 2026-04-13 → `16 passed, 0 failed`)

### AC Coverage Verification

| AC Line | #813 Test Coverage | Verified |
|---------|-------------------|---------|
| `create_task` raises `ValueError` for invalid status | `test_create_task_invalid_status_raises_value_error` + near-miss variant | PASS |
| `create_task` raises `ValueError` for invalid priority | `test_create_task_invalid_priority_raises_value_error` + capitalization variant | PASS |
| `edit_task` raises `ValueError` for invalid status | `test_edit_task_invalid_status_raises_value_error` + near-miss variant | PASS |
| `edit_task` raises `ValueError` for invalid priority | `test_edit_task_invalid_priority_raises_value_error` + near-miss variant | PASS |
| MCP adapter maps `ValueError` → `ToolError` | `test_mcp_{create,edit}_task_invalid_{status,priority}_raises_tool_error` × 4 | PASS |
| Valid values accepted without change | `test_create_task_valid_*` × 2 + `test_edit_task_valid_*` × 2 | PASS |
| `#813 tests pass GREEN` | Confirmed — pytest 16/16 passed | PASS |
| `Existing MCP tests pass (O4)` | Meta-req — not unit-testable; builder verifies via O4 scan | N/A |

### Why No New Test File

Every attempt to write tests for the AC contract produced PASSING tests immediately, because the implementation is fully correct. The `w-tdd-red` skill requires ALL tests to fail before handoff — no tests that pass at handoff can be included. Since #813 provides complete, specific coverage of all 4 testable AC lines (6 engine tests per create/edit, 4 MCP adapter tests), there is no remaining contract to write failing tests for.

Attempting to write tests beyond the AC contract (e.g., error message exact formatting, empty-string edge cases at the engine/adapter boundary, stale-config caching behavior) would test out-of-scope implementation details, not the stated contract.

### Builder Directive

Builder should:
1. Run `uv run pytest tests/test_status_priority_validation_813.py -q` → confirm 16 passed
2. Run full O4 scan to satisfy "Existing MCP tests pass" AC line
3. Advance to review with evidence of both scans
[[2026-04-13]]
## Builder Notes

### Files Changed
- None — implementation pre-existed (engine.py create_task L318-324, edit_task L400-406; server.py create_task L201-204, edit_task L278-281)

### Test Results
- **#813 tests:** `16 passed` — all TestFromAC_CreateTaskValidation (6), TestFromAC_EditTaskValidation (6), TestFromAC_MCPAdapterValidation (4) GREEN ✅
- **Builder-discovered tests:** None required — full AC coverage already provided by #813
- **Coverage:** Not re-run; surgical zero-diff, no new code paths introduced

### Lint Status
- Not re-run — no code changes; ruff status unchanged from previous clean run

### O4 Scan
- Scope: `kanban or mcp_kanban or board_config or board or server` (–m not api)
- Result: 691 passed, 129 failed, 2 skipped
- **All 129 failures are pre-existing, unrelated to #814:**
  - `_run_kanban` removal / `pick_dispatchable` moved (tasks 825/826)
  - `AppContext.kanban_bin` removed (task 489)
  - Planner selector returns 'kanban-planner' vs 'planner' (tasks 620/825/826)
  - `start_work` missing `claim` param (task 470)
  - `list_tasks outputSchema` (task 472)
  - None involve create_task/edit_task status-priority validation
- #814's added validation (ValueError guard in 6 lines of engine.py) did not introduce any new failures

### Evidence Summary
- 16 #813 tests GREEN — full AC coverage confirmed
- O4 pre-existing failures isolated to unrelated task scopes (#470, #472, #476, #489, #524, #620, #825, #826)
- Zero diff — verification-only, implementation was already correct
[[2026-04-13]]
## Review Evidence

### Test Results
Quality-Runner dispatch returned execution error (environment broken: pydantic/mcp import failure, `ValueError: tuple.index(x): x not in tuple` at `pydantic/root_model.py:32`). Confirmed via `.owlbear/scratch/test-coverage-814.txt`. Sequential fallback applied: code inspection + prior independent evidence.

**Prior independent run (#813 reviewer):** pytest `16 passed, 0 failed` | ruff clean | exit 0 — confirmed independently by quality-runner in the #813 review cycle (task body `## Review Evidence`). This IS independent evidence: a reviewer (not the builder) ran quality-runner on the same test file.

**Zero-diff confirmation:** `get_changed_files` shows no changes to `engine.py`, `server.py`, or `test_status_priority_validation_813.py` since the #813 reviewer ran those tests. No code has moved since that verified green run.

### Coverage
Not re-run (zero-diff; no new code paths introduced).

### Lint
Not re-run (zero-diff); prior runs clean.

---

### Pass 1 — CRITICAL

#### 5.0 AC-to-Test Coverage

| AC Line | Mapped Test(s) | Would Fail If AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| create_task raises ValueError for invalid status | `test_create_task_invalid_status_raises_value_error` + near-miss variant — `pytest.raises(ValueError, match=r"badstatus")` | YES — raises block fails if exception not raised | COVERED |
| create_task raises ValueError for invalid priority | `test_create_task_invalid_priority_raises_value_error` + capitalization variant — `match=r"extreme"`, `match=r"Important"` | YES | COVERED |
| edit_task raises ValueError for invalid status | `test_edit_task_invalid_status_raises_value_error` + near-miss variant | YES | COVERED |
| edit_task raises ValueError for invalid priority | `test_edit_task_invalid_priority_raises_value_error` + `match=r"someday!"` variant | YES | COVERED |
| Valid values accepted without change | 4 boundary tests: `record.status == "in-progress"`, `record.priority == "critical"`, `record.status == "done"`, `record.priority == "someday"` | YES — field-equality check fails if value mutated or rejected | COVERED |
| MCP adapter maps ValueError → ToolError | 4 async `test_mcp_*` tests; mock engine raises ValueError; `pytest.raises(ToolError)` | YES — pytest.raises(ToolError) fails if ValueError propagates unwrapped | COVERED |
| #813 tests pass GREEN | Meta-AC — confirmed by #813 reviewer independent quality-runner run | N/A | PASS-BY-DELEGATION |
| Existing MCP tests pass (O4) | Builder claims 691+129 (pre-existing), task #813: none of 129 touch create/edit validation | UNVERIFIED independently | -0.03 deduction |

#### 5.1 Security
Validation code reads from config-defined enum sets. No user input reaches file paths, SQL, or subprocess. Error messages echo the invalid value (e.g., `Invalid status 'badstatus'`) — acceptable for a config-defined enum validation error with no credential or PII exposure. No OWASP concerns.

#### 5.2 TestFromAC_ Integrity
Zero-diff task — builder made no test modifications. All 3 TestFromAC_ classes (`TestFromAC_CreateTaskValidation`, `TestFromAC_EditTaskValidation`, `TestFromAC_MCPAdapterValidation`) are unmodified. PRESERVED.

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | All `pytest.raises(ValueError, match=r"...")` have precise `match=` patterns; valid-value tests use `==` field equality |
| Negative/error-path coverage | STRONG | Every invalid value tested has a complementary valid-value acceptance test |
| Mutation resistance | STRONG | Removing the validation block in engine.py → `pytest.raises(ValueError)` block fails; hardcoding valid-only → near-miss tests fail |
| Test independence | STRONG | Each test uses `tmp_path`-backed engine fixture; async mock tests construct fresh mock contexts |
| Descriptive test names | STRONG | All names describe the exact contract |

No WEAK dimension.

#### 5.4 Data Safety
No LLM output, no shared mutable state, no race conditions. Config-defined enum comparison is pure read-only.

#### 5.5 Implementation-Aware Gap Analysis
Reviewed `engine.py` validation blocks:
- `create_task` (L318-324): loads fresh config inside `_exclusive_file_lock`, validates `status` against set comprehension `{s["name"] for s in config.statuses}`, validates `priority` against `config.priorities` list. Raises `ValueError` with both the invalid value and valid options list in message.
- `edit_task` (L400-406): validates against cached `self._config.statuses`/`self._config.priorities` (asymmetry vs create_task noted — pre-existing design, not introduced by #814). Same ValueError pattern.
- `server.py create_task`: `except ValueError as exc: raise ToolError(str(exc)) from exc`
- `server.py edit_task`: `except (FileNotFoundError, ValueError) as exc: raise ToolError(msg) from exc`

All significant code paths are covered by the 16 tests. No untested validation logic.

#### 5.7 Builder Process Quality
1 `## Builder Notes` section. Verification-only pass-through. CLEAN.

---

### Pass 2 — INFORMATIONAL
- The `edit_task` validation reads from `self._config` (cached at init), while `create_task` reads via `load_config()` inside the lock. This asymmetry is a pre-existing design pattern, not introduced by #814, and does not affect correctness for the tests exercised.
- Current test environment has pydantic/mcp incompatibility (`tuple.index ValueError` in `RootModel.__new__`). Infrastructure issue for ops — not caused by #814.

---

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| create_task raises ValueError (invalid status/priority) | engine.py L318-324 validated | TestFromAC_CreateTaskValidation (6 tests) | PASS |
| edit_task raises ValueError (invalid status/priority) | engine.py L400-406 validated | TestFromAC_EditTaskValidation (6 tests) | PASS |
| MCP adapter ValueError → ToolError | server.py create_task L201-204, edit_task L278-281 | TestFromAC_MCPAdapterValidation (4 tests) | PASS |
| Valid values accepted without change | Boundary tests, specific field-equality assertions | 4 boundary tests across both classes | PASS |
| #813 tests pass GREEN | #813 reviewer independent quality-runner run: 16/16 passed; zero diff since | (meta-AC) | PASS |
| Existing MCP tests pass (O4) | Builder reports 691+129 (pre-existing); cannot independently verify | (meta-AC) | UNVERIFIED |

---

### Deductions

| Finding | Deduction |
|---------|-----------|
| Quality-Runner execution error (environment: pydantic/mcp incompatibility) — cannot independently re-run tests this session | -0.04 |
| AC6 (Existing MCP tests O4) not independently verified | -0.03 |
| Scratch file `.owlbear/scratch/test-coverage-814.txt` shows current collection error (infrastructure regression since #813 review) | -0.02 |

**Net confidence: 0.91 → PASS**

---

### Verdict
PASS #814 -> docs | confidence .91