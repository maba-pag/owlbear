---
id: 1173
title: Fix server.py L481 status_names dict-form and stale test mock
status: in-progress
priority: needed
created: 2026-04-28T22:57:44.273925+00:00
updated: 2026-04-29T01:42:05.651474+00:00
tags:
- scope:mcp-kanban
- bugfix
parent:
depends_on: []
blocked: false
block_reason:
claimed_by: salt-elk
claimed_at: 2026-04-29T01:42:05.651474+00:00
archival_reason:
archival_refs: []
---

## Context

server.py L481 does `[s["name"] for s in board_config().statuses]` but statuses is list[str] post-Brief-C. Fix: replace with `list(app_ctx.engine.board_config().statuses)`. Also fix stale mock in test_mcp_lifecycle_tools.py L76 that uses list[dict] form.

## Acceptance Criteria

1. server.py L481 changed to `list(app_ctx.engine.board_config().statuses)` (or equivalent direct list usage)
2. test_mcp_lifecycle_tools.py mock updated to use list[str] for statuses
3. Existing guidance tests in test_guidance_rules_973.py and test_guidance_move_task_973.py still pass
4. move_task MCP tool entry point returns non-empty guidance list when forward-skip condition is met (adapter-level proof, not just collect_guidance helper)

## Affected files

- serve/mcp-kanban/src/owlbear_mcp_kanban/server.py
- serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One bug (dict-form on list[str]) + its stale test mock — same root cause |
| Interface clarity | PASS | AC specifies exact file, line, and replacement pattern |
| Dependency correctness | PASS | No deps needed; self-contained within mcp-kanban |
| Module layering | PASS | Both files in mcp-kanban package, no cross-package changes |
| TDD compliance | PASS | Test-writer will create RED tests from AC |
| KISS/YAGNI | PASS | 1-line fix + mock correction, no new abstractions |
| Premise challenge | PASS | Bug confirmed: BoardConfig.statuses is list[str] (models.py L149), server.py L481 does s["name"] on strings → TypeError silently swallowed by contextlib.suppress |
| Pattern consistency | PASS | Fix aligns with cockpit routes pattern (already uses list[str] correctly) |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Both files in mcp-kanban domain |

### AC Refinements (challenger-driven)
- AC3: Broadened regression scope to include adapter-level suites
- AC4: Clarified that proof must be at the move_task MCP tool entry point

### Challenge Results
- Challenger: reconsider (0.62)
- Key concerns: AC3 cited only helper-level suite; AC4 proof chain needs adapter-level binding
- Architect response: accepted — tightened AC3 and AC4 wording. Impact scoping concern (fallback vs primary path) is valid context but doesn't change the fix; the code is wrong regardless of path dominance.

### Verdict: APPROVE
### Action Taken: Refined AC3/AC4 for adapter-level proof, advanced to todo
[[2026-04-28]]
Architect approved. AC refined per challenger feedback: AC3 broadened to include adapter-level regression suites, AC4 requires move_task entry-point proof. All 10 architecture criteria PASS.
[[2026-04-28]]
## Test-Writer Notes

**Test file:** `tests/test_mcp_lifecycle_1173.py`

**Approach:** Tests import `_make_engine_mock` from `test_mcp_lifecycle_tools.py` via `importlib.util.spec_from_file_location`. This means the tests automatically pass once the builder updates the stale mock — no test file changes needed after the builder's fix.

**Why this design:** The L481 server.py code is already fixed (`list(engine.board_config().statuses)`). The stale mock at L76 of `test_mcp_lifecycle_tools.py` is harmless for existing tests (AgentView path returns before L481 is reached), but it prevents guidance from flowing correctly through the fallback path. Tests force `engine.agent_view = None` to activate the L481 fallback.

**Classes:**
| Class | AC | Tests |
|---|---|---|
| `TestFromAC_StatusNamesMockContract` | AC2 | 2 |
| `TestFromAC_MoveTaskGuidanceViaMock` | AC4 | 3 |

**Category breakdown:**
- Happy path: 1 (`test_forward_skip_more_than_one_slot_returns_guidance`)
- Boundary: 1 (`test_engine_mock_statuses_are_list_of_strings`)
- Error/regression: 1 (`test_engine_mock_statuses_contain_expected_pipeline_columns`)
- Message content: 2 (source/target status in guidance message)

**Total: 5 tests, all FAIL**

**pytest result:** `5 failed, 0 passed`

**Failure root cause (all 5):** `_make_engine_mock` sets `statuses = [{"name": s} for s in [...]]` (dict-form). With `engine.agent_view = None`, L481 runs: `list(engine.board_config().statuses)` = `[{"name": "research"}, ...]`. `_move_guidance` calls `status_names.index("research")` → `ValueError` (str not in list[dict]) → returns `[]` → guidance empty.

**AC coverage:**
| AC | Covered by |
|---|---|
| AC1: server.py L481 uses `list()` | Already satisfied (covered by `test_server_1172.py`) |
| AC2: mock uses list[str] | `TestFromAC_StatusNamesMockContract` (2 tests) |
| AC3: guidance tests still pass | Pre-existing; no new tests needed — `test_guidance_rules_973.py` and `test_guidance_move_task_973.py` currently pass (confirmed) |
| AC4: adapter-level guidance proof | `TestFromAC_MoveTaskGuidanceViaMock` (3 tests) |

**Ruff:** Clean (0 issues)
[[2026-04-29]]
## Builder Notes
- Implementation: updated [serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py](serve/mcp-kanban/tests/test_mcp_lifecycle_tools.py#L76) mock `engine.board_config.return_value.statuses` from `list[dict]` to `list[str]`.
- Source check: [serve/mcp-kanban/src/owlbear_mcp_kanban/server.py](serve/mcp-kanban/src/owlbear_mcp_kanban/server.py#L481) already uses `status_names = list(app_ctx.engine.board_config().statuses)` (AC1 already satisfied before this build).
- RED verification (quality-runner, task-scoped): `tests/test_mcp_lifecycle_1173.py` -> 0 passed / 5 failed, all failures matched stale mock shape + empty guidance symptoms.
- GREEN verification (quality-runner, task-scoped after fix): `tests/test_mcp_lifecycle_1173.py` -> 5 passed / 0 failed; ruff clean.
- AC3 regression verification (quality-runner with guidance suites): `serve/mcp-kanban/tests/test_guidance_rules_973.py` and `serve/mcp-kanban/tests/test_guidance_move_task_973.py` produced 24 passed / 1 failed total.
- Blocking mismatch test: `TestFromAC_MoveTaskGuidanceIntegration::test_archive_move_returns_empty_guidance` calls `move_task(..., status="archived")` without `archival_reason` and now raises ToolError mapped from engine validation (`archival_reason is required when status='archived'`).
- Routing decision: reject to test-writer because this is a test-interface mismatch against current move_task archived contract, and builder must not modify `TestFromAC_*` classes in durable suites.

Test-writer: update archived guidance test contract to include required `archival_reason` (or assert ToolError if archived-without-reason is intended invalid input), then return to in-progress for final AC3 gate re-check.

Post-task reflection:
- Problem faced: AC3 references a durable guidance test whose archived input no longer matches current validation contract.
- Workaround applied: separated task-scoped GREEN proof from broader regression gate with dedicated quality-runner runs.
- Pattern discovered: stale durable `TestFromAC_*` contracts can block otherwise-correct narrow fixes; contract validation should be rechecked before builder gate.
- Quality gap: AC3 broad gate did not declare archived-status preconditions, creating latent ambiguity during GREEN verification.
[[2026-04-29]]
## Test-Writer Notes

**Retry cycle** — stale contract fix in `serve/mcp-kanban/tests/test_guidance_move_task_973.py`.

**Root cause:** `test_archive_move_returns_empty_guidance` called `move_task(..., status="archived")` without `archival_reason`. Engine now requires `archival_reason` when archiving → ToolError → AC3 gate blocked.

**Fix:** Added `archival_reason="completed"` to the `move_task` call in the test. No logic change — the assertion (empty guidance for archive moves) is still correct and still holds.

**Verification (all 25 tests pass):**
- `serve/mcp-kanban/tests/test_guidance_move_task_973.py` → 5/5 passed (including updated archived test)
- `serve/mcp-kanban/tests/test_guidance_rules_973.py` → 15/15 passed (AC3 regression clean)
- `tests/test_mcp_lifecycle_1173.py` → 5/5 passed (builder's mock fix GREEN)

**AC coverage:**
| AC | Status |
|---|---|
| AC1: server.py L481 uses `list()` | Covered by `test_server_1172.py` (pre-existing) |
| AC2: mock uses list[str] | `TestFromAC_StatusNamesMockContract` (2 tests, GREEN) |
| AC3: guidance tests still pass | All 25 pass — including fixed archived test |
| AC4: adapter-level guidance proof | `TestFromAC_MoveTaskGuidanceViaMock` (3 tests, GREEN) |