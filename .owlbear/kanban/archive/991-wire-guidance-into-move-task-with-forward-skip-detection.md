---
id: 991
title: Wire guidance into `move_task` with forward-skip detection
status: archived
priority: needed
created: 2026-04-18T21:23:00.874612+00:00
updated: 2026-04-19T02:15:04.578213+00:00
tags:
- type:feature
- scope:mcp
- scope:kanban
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D2, D6.

## Problem

MCP `move_task` has no forward-skip detection. Currently delegates directly to engine without pre-reading the task.

## Acceptance Criteria

- `move_task` pre-reads the task via `_show_validated()` before calling `engine.move_task`.
- After engine call, calls `collect_guidance("move", before=pre_read_task, after=result_task, status_names=[s["name"] for s in board_config().statuses])`.
- Forward skip > 1 slot returns guidance with forward-skip message.
- Forward skip of exactly 1 slot → empty guidance.
- Backward moves → empty guidance.
- Moves to `archived` → empty guidance (excluded from skip detection).
- Integration test per case.

## Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/tests/test_guidance_move_task_973.py` (new)

## Dependencies

- Depends on: KanbanTask.guidance field task, guidance.py module task
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/move-task-guidance-991.md
- Sources: 7 studied, 6 high-relevance (all codebase-internal)
- Recommendation: Proceed with Brief Path A1, locked decisions D2/D6 — pre-read via `_show_validated()`, extract `status_names` from `board_config().statuses`, wire `collect_guidance("move", ...)` with try/except (confidence: .92)
- Key findings: (1) `move_task` is the only integration needing `before` state — uses existing `_show_validated()`. (2) `board_config().statuses` never includes archived, so skip detection auto-excludes archived moves. (3) TOCTOU between pre-read and engine call accepted per Brief R1.4. (4) Implementation is ~15 LOC, pattern identical to validated siblings #985/#989.
- Challenge: SKIPPED — approach locked via parent Brief 3-round architect debate
- Follow-up tasks created: none (task itself moves to backlog; deps #986/#987 exist)
- Decision requests: none — T1 autonomous, all decisions locked
- Dependencies: needs [986, 987] wired to `depends_on` before entering in-progress
[[2026-04-18]]

## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `move_task` pre-reads via `_show_validated()` before `engine.move_task` | PASS — `_show_validated` exists at server.py L169-176, returns `KanbanTask` | None |
| After engine call, calls `collect_guidance("move", before=..., after=..., status_names=[...])` | PASS — call signature consistent with #987 AC Refinement #1 (`status_names` kwarg) | None |
| Forward skip > 1 slot → guidance with message | PASS — verifiable integration test | None |
| Forward skip exactly 1 slot → empty guidance | PASS — verifiable integration test | None |
| Backward moves → empty guidance | PASS — verifiable integration test | None |
| Moves to `archived` → empty guidance | PASS — `board_config().statuses` never includes archived; auto-excluded | None |
| Integration test per case | PASS — 4 cases mapped in research §3.5; file `test_guidance_move_task_973.py` consistent with sibling naming | None |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One integration wiring: guidance into `move_task` |
| Interface clarity | PASS | `move_task` signature unchanged; output gains populated `guidance` field. Pre-read, guidance call, try/except pattern matches siblings |
| Dependency correctness | PASS (needs wiring) | Depends on #986 (model field, todo) and #987 (guidance module, todo). `depends_on` must be set to [986, 987] — not possible via `end_work`; noted for manual wiring |
| Module layering | PASS | `server.py` imports `collect_guidance` from `guidance.py` — same package, no upward imports |
| TDD compliance | PASS | Test file specified; task flows through test-writer |
| KISS/YAGNI | PASS | ~15 LOC: pre-read + guidance call + try/except. Minimal, pattern-identical to siblings #985/#989 |
| Premise challenge | PASS | Required by parent Brief D2/D6 for forward-skip detection |
| Pattern consistency | PASS | Uses existing `_show_validated`, `_record_to_task`, `asyncio.to_thread` patterns |
| Security surface | PASS | No new system boundaries; guidance strings are internal advisory text |
| Single domain | PASS | MCP kanban domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `_show_validated` pre-read fails | move_task fails before engine call | ToolError | Yes — existing pattern | Clean error, no state change |
| `collect_guidance()` raises | Guidance lost | Any | Yes — try/except per parent #973 arch guidance note #5 | Operation succeeds, empty guidance |
| Missing `status_names` kwarg | Forward-skip rule returns [] | None | By design (defensive `kwargs.get`) | No skip guidance, operation succeeds |
| TOCTOU: status changes between pre-read and engine move | Guidance reports stale delta | N/A | Accepted per Brief R1.4 | Possible spurious skip warning (advisory) |

### Challenge Results

- Challenger: `reconsider` (confidence 0.55)
- Key concerns: C1 (`status_names` vs `statuses` kwarg mismatch with existing pre-approval code), C2 (existing guidance.py predates #987 approval), C3 (`before` type annotation), C4 (duplicate RED task #979), C5 (research skipped challenge)
- Architect response: REBUTTED

**C1 rebuttal (kwarg naming — critical):** The existing `guidance.py` uses `statuses`, but #987's architecture review AC Refinement #1 is binding: "Builder must use `status_names`, not `statuses`." The TDD pipeline enforces this: test-writer writes tests per approved AC using `status_names`, builder implements to pass those tests, reviewer verifies. Since #991 depends on #987, by the time #991 enters implementation, #987 will have completed its TDD cycle with the approved naming. The `**kwargs` fragility concern is valid in general, but the pipeline's test-first enforcement is the mitigation. Additionally, the defensive `kwargs.get("status_names", [])` pattern means a naming mismatch produces empty guidance (safe failure), not an exception.

**C2 rebuttal (existing code):** Same concern raised and rebutted in #987's architecture review. Pre-approval code is not authoritative. #987's TDD cycle will validate or replace it.

**C3 rebuttal (`before` type):** #991 always provides `before` from `_show_validated()` — never `None`. The `Optional` type annotation is #987's concern, not #991's.

**C4 rebuttal (duplicate #979):** #979 is from an earlier decomposition (depends on #976, not #987). The current decomposition tree (#986→#987→#991) supersedes it. #979 should be cleaned up by the orchestrator, not a blocker for #991.

**C5 rebuttal (research skipped challenge):** Research challenge-skipping for locked decisions is appropriate. This architecture review IS the adversarial review for implementation details — and the challenger was invoked here.

### Observations

1. **Dependency wiring required.** `depends_on` must be set to [986, 987]. Both are in `todo`. Not possible via `end_work`; requires manual wiring before this task enters in-progress.
2. **Stale task #979.** Earlier decomposition created #979 ("RED: move_task guidance + pre-read tests") with dependency on #976. This overlaps #991's integration tests. Recommend archiving #979 or reconciling with the current decomposition under #973.
3. **try/except wrapping.** Not explicit in AC but mandated by parent #973 arch review Implementation Guidance note #5. Builder should follow the sibling pattern from #985/#989.

### Verdict: APPROVE

### Action Taken: Advanced to todo. Dependency wiring [986, 987] and stale #979 cleanup noted for manual resolution

[[2026-04-19]]

## Test-Writer Notes

- **Premature implementation detected.** Both implementation and test file were committed in `161e4c2d` (feat: block-time guidance from owlbear-kanban MCP, #973, builder) before this task reached the test-writer phase.
- **Test file:** `serve/mcp-kanban/tests/test_guidance_move_task_973.py` (committed, clean)
- **Class:** `TestFromAC_MoveTaskGuidanceIntegration`
- **Test count:** 5 integration tests
- **Categories:** happy (forward skip >1, 1-slot, message content), edge (backward move, archive move)
- **RED verification:** NOT achievable — all 5 tests pass because implementation is complete. `pytest serve/mcp-kanban/tests/test_guidance_move_task_973.py` → `5 passed`.
- **AC coverage:** All 7 AC lines covered (4 behavioral cases + wiring verified by outcome assertions).

| AC Line | Test(s) |
|---|---|
| pre-read via `_show_validated()` before engine call | `test_forward_skip_guidance_references_from_and_to_status` (verifies before-state captured) |
| `collect_guidance("move", before=..., after=..., status_names=[...])` | all 4 case tests verify wiring output |
| Forward skip > 1 slot → guidance message | `test_forward_skip_more_than_one_slot_returns_guidance` |
| Forward skip = 1 slot → empty | `test_forward_skip_one_slot_returns_empty_guidance` |
| Backward move → empty | `test_backward_move_returns_empty_guidance` |
| Archived → empty | `test_archive_move_returns_empty_guidance` |
| Integration test per case | ✓ all 4 cases present |

**Builder action required:** Implementation and tests are pre-existing. Builder should verify, run the test suite, and commit under #991 if no changes are needed (or note pass-through).
[[2026-04-19]]

## Builder Notes

**Verification pass-through** — implementation was pre-committed in `161e4c2d` (feat: block-time guidance from owlbear-kanban MCP, #973 builder) before this task reached the test-writer phase.

### Files changed

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — `move_task` pre-reads via `_show_validated()`, calls `collect_guidance("move", before=pre_task, after=result, status_names=[...])` wrapped in `contextlib.suppress(Exception)`. Matches sibling pattern from #985/#989.
- `serve/mcp-kanban/tests/test_guidance_move_task_973.py` — 5 integration tests (pre-existing)

### Test results

- `pytest serve/mcp-kanban/tests/test_guidance_move_task_973.py -v --tb=short -n 0` → **5 passed** (0.41s)
- All 5 `TestFromAC_MoveTaskGuidanceIntegration` cases pass: forward-skip >1, forward-skip 1-slot, backward, archive, message content

### Lint

- `ruff check serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` → **All checks passed**

### Evidence summary

- AC wiring verified at server.py L215-228: `_show_validated()` pre-read (L215), `collect_guidance` call (L228) with correct `status_names` kwarg, `contextlib.suppress` safety wrapper (L226)
- No new files, no dependencies added, no builder-discovered issues
- No commit needed — implementation already in tree under `161e4c2d`
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 5 passed, 0 failed — `serve/mcp-kanban/tests/test_guidance_move_task_973.py`

### Lint

clean: true (ruff on server.py and test file)

### Coverage

- `owlbear_mcp_kanban.server`: 42% — expected for scoped tests targeting only `move_task`; all touched lines exercised

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If Violated? | Verdict |
|---------|-------------|------------------------|---------|
| `move_task` pre-reads via `_show_validated()` before `engine.move_task` | `test_forward_skip_more_than_one_slot_returns_guidance` (implicit — `pre_task=None` collapses guidance) | Yes | COVERED |
| `collect_guidance("move", before=pre_task, after=result, status_names=[...])` | All 4 behavioral tests | Yes — wrong/missing call collapses all 4 | COVERED |
| Forward skip > 1 slot → guidance | `test_forward_skip_more_than_one_slot_returns_guidance` | Yes — `assert len(result.guidance) > 0` | COVERED |
| Forward skip = 1 slot → empty | `test_forward_skip_one_slot_returns_empty_guidance` | Yes — `assert result.guidance == []` | COVERED |
| Backward move → empty | `test_backward_move_returns_empty_guidance` | Yes — `assert result.guidance == []` | COVERED |
| Archived → empty | `test_archive_move_returns_empty_guidance` | Yes — `assert result.guidance == []` | COVERED |
| Integration test per case | All 4 direct cases present | Fulfilled by test existence | COVERED |

No MISSING entries.

#### Security Review

No issues. Inputs arrive through Pydantic-validated `StrId`/`str`. No shell invocation, no user-controlled file paths, no hardcoded secrets, no unsafe deserialization. `board_config().statuses` is engine-internal, not user-controlled.

#### Test Integrity

No `TestFromAC_*` tests modified. All 5 tests match RED-phase intent. No relaxed assertions, no `skip`/`xfail` added. PRESERVED.

#### Test Quality

| Dimension | Rating |
|-----------|--------|
| Assertion specificity | ADEQUATE — forward-skip uses `len > 0` (lazy) but compensated by `test_forward_skip_guidance_references_from_and_to_status` asserting both status strings in message; empty-guidance tests use `== []` (strong) |
| Negative/error-path coverage | STRONG — 3 of 4 tests are "no guidance" cases |
| Mutation resistance | ADEQUATE — flipping `delta > 1` → `delta >= 1` breaks 1-slot test; removing pre-read collapses forward-skip |
| Test independence | STRONG — fresh `AppContext` + `tmp_path` per test |
| Descriptive names | STRONG — all five names precisely describe scenario and outcome |

Overall: ADEQUATE. No WEAK dimension.

#### Data Safety

No new data safety issues. Guidance is non-persisted advisory output. `contextlib.suppress(Exception)` is the established defensive pattern at all 4 guidance sites in this file — consistent, documented by sibling precedent.

#### Test Gaps

One untested defensive branch: `contextlib.suppress(Exception)` in guidance block (server.py:226–228) — if `board_config()` raises, exception is silently swallowed, empty guidance returned. Not blocking: identical untested pattern exists at `edit_task` and `end_work` guidance sites; behavior is safe (advisory guidance, operation still succeeds).

#### Builder Process Quality

CLEAN — single pass-through (pre-committed in `161e4c2d`). No retries.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| Pre-read via `_show_validated()` | server.py:215 `pre_task = await _show_validated(app_ctx, task_id)` | PASS |
| `collect_guidance("move", before=..., after=..., status_names=[...])` | server.py:226–228 with `contextlib.suppress` wrapper | PASS |
| Forward skip >1 → guidance | test passes: `len(result.guidance) > 0` | PASS |
| Forward skip =1 → empty | test passes: `result.guidance == []` | PASS |
| Backward → empty | test passes: `result.guidance == []` | PASS |
| Archived → empty | test passes: `result.guidance == []` | PASS |
| Integration test per case | 5 integration tests present and passing | PASS |

### Informational

- **Filename mismatch (non-blocking):** `test_guidance_move_task_973.py` references task 973 in the name but covers #991. File content is correct; only the name is misleading. Test-writer noted this.
- **Fixture coupling:** `engine.list_tasks()` call in fixture (line 86) populates internal id→filename cache — comment explaining the reason would help future readers.

### Verdict

0 deductions. Confidence: **.95 → PASS**
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A | `move_task` now populates `guidance` field on forward-skip; `copilot-instructions.md` documents MCP server identity only, not tool output schemas — no update required |
| 2 | Module docstrings | Yes | Verified | `server.py:move_task` docstring: "Move a task to the specified status column, or archive it when status is 'archived'." — accurate, guidance output is an advisory field not requiring docstring change |
| 3 | External attribution | No | N/A | Research doc states all 6 high-relevance sources are codebase-internal — no new row needed in sources |
| 4 | CLI changes | No | N/A | MCP tool only; no CLI surface changed |
| 5 | Research doc | Yes | Verified | `.owlbear/research/move-task-guidance-991.md` exists and is linked in task body |

### Files Updated

None — no documentation files required changes.

### Scratch Files

No `.owlbear/scratch/991-*` files found — nothing to clean.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| Pre-read via `_show_validated()` before `engine.move_task` | server.py:215 `pre_task = await _show_validated(app_ctx, task_id)` | PASS |
| `collect_guidance("move", before=..., after=..., status_names=[...])` | server.py:226-228 with `contextlib.suppress` wrapper | PASS |
| Forward skip >1 slot returns guidance | `test_forward_skip_more_than_one_slot_returns_guidance` passes | PASS |
| Forward skip =1 slot returns empty | `test_forward_skip_one_slot_returns_empty_guidance` passes | PASS |
| Backward moves return empty | `test_backward_move_returns_empty_guidance` passes | PASS |
| Moves to archived return empty | `test_archive_move_returns_empty_guidance` passes | PASS |
| Integration test per case | 5 tests in `TestFromAC_MoveTaskGuidanceIntegration` covering 4 behavioral cases + message content | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all 6 in mcp-knowledge — unrelated to #991 scope), 0 skipped
- ruff: clean (0 violations)

### Architect Quality: 4/5

AC lines were specific and verifiable. All behavioral cases covered. Minor gap: `contextlib.suppress` wrapping not explicit in AC but mandated by parent #973 arch guidance note #5 — builder/reviewer handled it cleanly. Filename `test_guidance_move_task_973.py` uses parent task id rather than #991 — misleading but non-blocking, noted by reviewer.

### Deduction Breakdown

- AC lines with no evidence: 0 (all 7 PASS) — no deduction
- Lint violations: 0 — no deduction
- AC quality score 4/5 (>3) — no deduction
- Reviewer evidence section: present, detailed, PASS verdict — no deduction
- Full-suite failures in task scope: 0 — no deduction

### Confidence: .98

### Action: archive
