---
id: 813
title: Tests — status/priority validation
status: done
priority: needed
created: '2026-04-10T21:21:54.982332+00:00'
updated: '2026-04-12T09:14:10.242352+00:00'
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
[[2026-04-12]]
## Research
- Research doc: .owlbear/research/status-priority-validation-813.md
- Sources: 9 studied, 6 high-relevance
- Recommendation: Single test file (tests/test_status_priority_validation_813.py) with 14 tests across 3 classes — engine create_task validation (5), engine edit_task validation (5), MCP adapter ToolError mapping (4). Reuse fixture pattern from test_kanban_engine_crud.py. Strict ValueError/ToolError assertions. All tests RED against current code. (confidence: .95)
- Follow-up tasks created: none — #814 already exists as GREEN phase
- Decision requests: none
[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tests only for status/priority validation — one concern |
| Interface clarity | PASS | Inputs: invalid status/priority strings. Outputs: `ValueError`/`ToolError`. Clear from AC |
| Dependency correctness | PASS | No dependencies. Correct — this is the RED phase. #814 (GREEN) depends on this |
| Module layering | PASS | Tests use public API only (`KanbanEngine`, MCP adapter) |
| TDD compliance | PASS | This IS the RED phase test task; #814 is GREEN |
| KISS/YAGNI | PASS | 14 tests across 3 classes — appropriate scope, no speculation |
| Premise challenge | PASS | Validation gaps confirmed: `create_task` and `edit_task` lack status/priority validation. `move_task` has it (engine.py:396-412) — pattern to replicate |
| Pattern consistency | PASS | Follows existing `test_kanban_engine_crud.py` fixture pattern. Uses strict `pytest.raises(ValueError)` per AC (not the broader tuple in older move_task tests) |
| Security surface | PASS | Test-only task, no new system boundaries |
| Single domain | PASS | scope:mcp-kanban only |

### Codebase Verification

- `engine.py` `create_task` (L232-295): no status/priority validation — tests will correctly fail RED
- `engine.py` `edit_task` (L289-395): no status/priority validation — tests will correctly fail RED
- `engine.py` `move_task` (L396-412): existing `ValueError` validation pattern to replicate
- MCP `server.py` `create_task` (L177-206): no try/except — MCP tests will correctly fail RED
- MCP `server.py` `edit_task` (L217-278): catches `FileNotFoundError` only, not `ValueError` — MCP tests will correctly fail RED
- MCP `server.py` `move_task` (L205-211): existing `ValueError→ToolError` mapping pattern
- Config valid values: statuses=[research, backlog, todo, in-progress, review, docs, done], priorities=[someday, nice-to-have, important, needed, critical]
- No duplicate test coverage found

### Edge Case Note

`create_task` with empty status/priority falls back to defaults via `status or config.defaults.status` — this is correct behavior, not a validation error. MCP `edit_task` adapter skips empty strings (`if status:` is falsy). Builder should note this in RED tests.

### Challenge Results

- Challenger: proceed (confidence: 0.92)
- No duplicate tests, no AC gaps, RED phase confirmed
- Architect response: accepted

### Verdict: APPROVE
### Action Taken: Advanced to todo. AC is precise and verifiable. All 7 AC lines map to concrete assertions. Codebase patterns confirmed.
[[2026-04-12]]
## Test-Writer Notes

- **Test file:** `tests/test_status_priority_validation_813.py`
- **Classes:** `TestFromAC_CreateTaskValidation`, `TestFromAC_EditTaskValidation`, `TestFromAC_MCPAdapterValidation`
- **Tests per category:**
  - Happy/boundary (AC5 via combined tests): 2 (tests 5 and 10 — fail RED via inner pytest.raises)
  - Error/invalid (AC1–AC4): 8 (4 per engine class — DID NOT RAISE failures)
  - Adapter mapping (AC6): 4 (ValueError propagates uncaught, not ToolError)
- **Total:** 14 tests, **14 FAIL** confirmed via pytest
- **Lint:** ruff clean (PT011 resolved with `match=` on all `pytest.raises` blocks)
- **Commit:** `78a30c73`

### AC Coverage

| AC | Tests | RED Mechanism |
|---|---|---|
| AC1 – create_task invalid status | tests 1, 2, 5 | `DID NOT RAISE ValueError` — engine accepts all values |
| AC2 – create_task invalid priority | tests 3, 4 | `DID NOT RAISE ValueError` |
| AC3 – edit_task invalid status | tests 6, 7, 10 | `DID NOT RAISE ValueError` |
| AC4 – edit_task invalid priority | tests 8, 9 | `DID NOT RAISE ValueError` |
| AC5 – valid values accepted | tests 5, 10 (combined) | Fail at invalid-neighbor `pytest.raises` block — GREEN validates both sides |
| AC6 – MCP adapter ToolError mapping | tests 11–14 | `ValueError` propagates from mock (no try/except in adapter); `pytest.raises(ToolError)` fails |
[[2026-04-12]]
## Builder Notes

### Files Changed
- `serve/kanban/src/owlbear_kanban/engine.py` — added status/priority validation to `create_task` and `edit_task`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — added `ValueError→ToolError` mapping in `create_task` and `edit_task`

### Implementation
- `create_task`: validates `status` (if non-empty) and `priority` (if non-empty) against config after load; empty string still falls through to defaults
- `edit_task`: validates `status` (if not None) and `priority` (if not None) against `self._config`; None means "no change"
- Both follow the `move_task` pattern: `{s["name"] for s in config.statuses}` for statuses, `config.priorities` list for priorities
- MCP `create_task`: wrapped engine call in `try/except ValueError → ToolError`
- MCP `edit_task`: changed `except FileNotFoundError` to `except (FileNotFoundError, ValueError)`
- Fixed `SIM102` (nested if → combined with `and`); added `PLR0915` to `edit_task` noqa (statement count increase)

### Test Results
- **14 passed, 0 failed** (pytest, 6.81s) — all `TestFromAC_*` tests green
- RED verified first: 14 FAIL before implementation
- No `TestBuilderDiscovered` tests needed — no edge cases outside AC scope
- 6 pre-existing failures in `test_kanban_engine_listing.py` (scope: #815/#816, timestamp sort fix) — unrelated

### Lint
- ruff clean on all 3 modified/test files

### Commit
- `b1076925` — feat(mcp-kanban): add status/priority validation to create/edit_task (#814)
[[2026-04-12]]
## Review Evidence

### Test Results
- pytest: **14 passed, 0 failed** (independent run via quality-runner, retry required due to env bootstrap issue on first attempt)

### Lint
- ruff: **clean** — 0 violations across `engine.py`, `server.py`, `test_status_priority_validation_813.py`

### Coverage
- `owlbear_kanban.engine`: 38% (scoped test file only — expected; large module covered by other suites)
- `owlbear_mcp_kanban.server`: 53% (scoped test file only — expected)

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 – create_task raises ValueError for invalid status | test_create_task_invalid_status_raises_value_error, test_create_task_invalid_status_near_valid_raises_value_error | Yes — pytest.raises(ValueError) not satisfied if engine accepts invalid status | COVERED |
| AC2 – create_task raises ValueError for invalid priority | test_create_task_invalid_priority_raises_value_error, test_create_task_invalid_priority_near_valid_raises_value_error | Yes — same mechanism | COVERED |
| AC3 – edit_task raises ValueError for invalid status | test_edit_task_invalid_status_raises_value_error, test_edit_task_invalid_status_near_valid_raises_value_error | Yes | COVERED |
| AC4 – edit_task raises ValueError for invalid priority | test_edit_task_invalid_priority_raises_value_error, test_edit_task_invalid_priority_near_valid_raises_value_error | Yes | COVERED |
| AC5 – valid status/priority values accepted (from config) | test_create_task_valid_status_in_progress_accepted_underscore_rejected, test_edit_task_valid_status_done_accepted_typo_rejected | Yes — combined tests assert `record.status == "in-progress"` / `"done"` after valid call | COVERED |
| AC6 – MCP adapter maps ValueError to ToolError (create_task + edit_task) | tests 11–14 (all 4 async adapter tests) | Yes — pytest.raises(ToolError) fails if ValueError propagates uncaught | COVERED |
| AC7 – Tests fail RED before implementation | Test-writer confirmed 14 FAIL at commit 78a30c73; verified by test-writer notes | N/A — meta-requirement, documented | PASS (noted) |

#### 5.1 Security Review
- Whitelist validation only (`{s["name"] for s in config.statuses}`, `config.priorities` list) — no injection vectors
- Error messages use `{status!r}` / `{priority!r}` repr — safe, no PII leakage
- No new dependencies
- No hardcoded secrets
- **No issues**

#### 5.2 Test Integrity — TestFromAC Comparison
Builder changed only `engine.py` and `server.py`. Test file (`test_status_priority_validation_813.py`) unmodified. No TestFromAC_ methods weakened or removed.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 14 TestFromAC_ tests | No changes by builder | PRESERVED |

#### 5.3 Test Quality
- **Assertion specificity**: Engine tests use `pytest.raises(ValueError, match=r"...")` with the invalid value in the pattern — value would have to appear in error message. MCP tests use `pytest.raises(ToolError)` without match= (appropriate — the key assertion is wrapping behavior, not message content; mock controls the exact ValueError). STRONG.
- **Negative/error-path coverage**: 8 invalid-value tests (4 per engine class) + 4 MCP adapter tests. STRONG.
- **Mutation reasoning**: Removing the `if status:` guard or `if priority and ...` block in engine.py would cause `pytest.raises(ValueError)` blocks to fail (DID NOT RAISE). STRONG.
- **Test independence**: All use `tmp_path`-based fixtures. No shared mutable state. STRONG.
- **Descriptive names**: All test names fully describe the scenario. STRONG.

Overall: **STRONG**

#### 5.4 Data Safety
No LLM output, no concurrent write paths introduced, no unbounded inputs. PASS.

#### 5.5 Implementation-Aware Test Gap Analysis
- `engine.py create_task` L246–253: `if status:` guard tested (empty string falls to default — implicitly tested in AC5 combined test creating "Hyphen good" with no explicit priority). Explicit values tested for both valid and invalid.
- `engine.py edit_task` L341–349: `if status is not None:` guard. Note: `status=""` would raise ValueError via engine direct call (empty string is not in valid_statuses), but MCP adapter filters empties with `if status: kwargs["status"] = status` (server.py L254). This asymmetry is expected by design (architecture review edge case note). Not an AC requirement. No gap.
- `server.py` create_task adapter L199–204: `except ValueError → ToolError` — covered by 2 async tests.
- `server.py` edit_task adapter L274–280: `except (FileNotFoundError, ValueError) → ToolError` — covered by 2 async tests.
- No significant untested paths.

#### 5.6 Necessity Check: N/A (no new dependencies)

#### 5.7 Builder Process Quality
- Single `## Builder Notes` section — **CLEAN**

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | engine.py L248: `raise ValueError(msg)` when status not in valid_statuses | tests 1, 2 | PASS |
| AC2 | engine.py L251–253: `raise ValueError(msg)` when priority not in config.priorities | tests 3, 4 | PASS |
| AC3 | engine.py L344–346: same pattern for edit_task | tests 6, 7 | PASS |
| AC4 | engine.py L347–349: same pattern for edit_task priority | tests 8, 9 | PASS |
| AC5 | engine.py L284: `status or config.defaults.status`; test L110–112: `assert record.status == "in-progress"`; test L192–193: `assert record.status == "done"` | tests 5, 10 | PASS |
| AC6 | server.py L202: `except ValueError as exc: raise ToolError(...)`; server.py L213: `except (FileNotFoundError, ValueError) as exc: raise ToolError(...)` | tests 11–14 | PASS |
| AC7 | test-writer notes: 14 FAIL at commit 78a30c73 | — | PASS |

### Informational Notes (Pass 2)
- Priority error messages show unsorted list repr (`['someday', ...]`) while status messages show `sorted(...)` set. Cosmetic inconsistency — tests unaffected (match= patterns target the invalid value only).

### Verdict
**0 deductions. Confidence: .95 → PASS**
[[2026-04-12]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` contains only project identity/branch info — no API behavior tables. No update needed. |
| 2 | Module docstrings | Yes | Updated | `engine.py` `create_task` and `edit_task` were missing `Raises: ValueError` documentation for the new status/priority validation. Added to both. Commit `1c646127`. |
| 3 | External attribution | No | N/A | Research doc sources are all internal (engine.py, server.py, test files, config.yml). No external repos or articles used. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | Yes | Verified | `.owlbear/research/status-priority-validation-813.md` exists and is linked from task body. Follow-up tasks noted as N/A (sibling #814 already existed). |

### Files Updated
- `serve/kanban/src/owlbear_kanban/engine.py` — added `Raises: ValueError` to `create_task` and `edit_task` docstrings (commit `1c646127`)

### Scratch Files
- No `.owlbear/scratch/813-*` files found — nothing to clean.
[[2026-04-12]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 – create_task raises ValueError for invalid status | engine.py L264-266: `raise ValueError(msg)` when status not in valid_statuses; tests 1-2 PASS | PASS |
| AC2 – create_task raises ValueError for invalid priority | engine.py L267-268: `raise ValueError(msg)` when priority not in config.priorities; tests 3-4 PASS | PASS |
| AC3 – edit_task raises ValueError for invalid status | engine.py L346-348: same pattern; tests 6-7 PASS | PASS |
| AC4 – edit_task raises ValueError for invalid priority | engine.py L349-350: same pattern; tests 8-9 PASS | PASS |
| AC5 – valid status/priority values accepted | tests 5, 10: combined valid+invalid assertions PASS | PASS |
| AC6 – MCP adapter maps ValueError to ToolError | server.py L203-204 (create_task), L277-280 (edit_task); tests 11-14 PASS | PASS |
| AC7 – Tests fail RED before implementation | Test-writer notes confirm 14 FAIL at commit 78a30c73 | PASS |

### Test Results
- pytest (task-scoped): 14 passed, 0 failed
- pytest (full suite): 3781 passed, 353 failed, 8 errors — all failures pre-existing, 0 in task scope
- ruff: clean — 0 violations

### Architect Quality: 5/5
All 7 AC lines are specific, testable, map to concrete assertions. Edge case (empty-string fallback) proactively documented. No builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (×-.02) = 0
- Lint violations: 0 (×-.05) = 0
- AC quality ≤ 3: No (×-.03) = 0
- Missing reviewer evidence: No (×-.02) = 0
- Full-suite failures in task scope: 0 (×-.05) = 0

### Confidence: 1.00
### Action: archive

### Commits Verified
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| 78a30c73 | test | tests/test_status_priority_validation_813.py | #813 |
| b1076925 | feat | engine.py, server.py | #814 |
| 1c646127 | docs | engine.py docstrings | #813 |