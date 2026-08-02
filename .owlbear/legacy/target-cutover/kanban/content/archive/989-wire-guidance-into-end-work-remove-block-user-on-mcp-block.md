---
id: 989
title: Wire guidance into `end_work` + remove `block:user` on MCP block
status: archived
priority: medium
created: 2026-04-18T21:23:00.860323+00:00
updated: 2026-04-19T02:05:19.409511+00:00
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
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D2, D3.

## Problem

MCP `end_work` returns no guidance when blocking or succeeding. Also, `end_work(outcome="block")` should remove any stale `block:user` tag.

## Acceptance Criteria

- `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` after engine call.
- `end_work(outcome="block")` returns `guidance` containing the DR-required message.
- `end_work(outcome="block")` removes `block:user` tag if present.
- `end_work(outcome="success")` returns `guidance` with commit-pushed reminder.
- `end_work(outcome="fail")` and `end_work(outcome="reject")` → empty guidance.
- Integration test per outcome.

## Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/tests/test_guidance_end_work_973.py` (new)

## Dependencies

- Depends on: KanbanTask.guidance field task, guidance.py module task
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/end-work-guidance-989.md
- Sources: 6 studied (all internal codebase), 4 high-relevance
- Recommendation: proceed with implementation per Brief Path A1 and locked decisions D2, D3 (confidence: .90)
- Challenge: SKIPPED — approach locked via parent Brief 3-round architect debate with 9 decisions
- Follow-up tasks created: none — #989 is already atomic with clear AC
- Decision requests: none — T1 autonomous (all decisions locked in Brief)

## Key Findings

1. **Non-atomic tag removal confirmed.** Engine `end_work` does NOT accept `remove_tags`. Sequential calls required: `engine.end_work()` → `engine.edit_task(task_id, remove_tags=["block:user"])`. Engine `edit_task` does not require a claim. Architect rebuttal C1 confirmed this path.
2. **Guidance attachment pattern.** Same as sibling #985: `_record_to_task(record)` → `collect_guidance("end_work", before=None, after=task, outcome=outcome)` → assign to `task.guidance`. Wrapped in try/except per architect note #5.
3. **Four outcomes mapped.** Block → DR guidance + tag removal. Success → commit reminder. Fail/reject → empty guidance. All clearly defined in AC and guidance module spec (#987).
4. **Dependencies #986 (model field) and #987 (guidance module) both in research.** Must be wired as `depends_on` before #989 enters in-progress. Both calls use `asyncio.to_thread`.
[[2026-04-18]]

## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` | PASS — consistent with #987 approved AC (operation="end_work", outcome as kwarg) | None |
| `end_work(outcome="block")` returns guidance with DR-required message | PASS — verifiable via integration test | None |
| `end_work(outcome="block")` removes `block:user` tag if present | PASS — sequential engine calls verified in parent C1 rebuttal | **REFINED** — specify ordering and re-read |
| `end_work(outcome="success")` returns guidance with commit-pushed reminder | PASS — verifiable | None |
| `end_work(outcome="fail")` and `end_work(outcome="reject")` → empty guidance | PASS — verifiable | None |
| Integration test per outcome | PASS — 4 outcomes, clear positive/negative cases | None |

### AC Refinements (binding for test-writer and builder)

1. **Execution ordering (was implicit, now explicit).** The `end_work` handler must execute in this order: (a) `engine.end_work()` → record, (b) if `outcome == "block"` and `"block:user"` in record tags → `engine.edit_task(task_id, remove_tags=["block:user"])` → updated record, (c) `_record_to_task(latest_record)` → task, (d) `collect_guidance("end_work", before=None, after=task, outcome=outcome)` → assign to `task.guidance`. The returned task must reflect post-tag-removal state.

2. **Error resilience (was missing, now explicit).** Both `collect_guidance()` and the `block:user` tag removal are wrapped in try/except. On failure: tag removal failure → tolerable (stale tag persists, log warning), guidance failure → return task with empty guidance. Neither failure prevents returning the tool result. Per parent #973 note #5.

3. **Dependency wiring (required).** `depends_on` must be set to `[986, 987]`. #986 provides the `guidance` field on `KanbanTask`; #987 provides the `collect_guidance()` function. Both are in `todo`. **NOTE:** `edit_task` tool not available in this session — orchestrator must wire `depends_on: [986, 987]` before this task enters in-progress.

4. **Interface contract reference.** AC1's call signature is consistent with #987's approved AC: `collect_guidance(operation: str, before: KanbanTask | None, after: KanbanTask, **kwargs) -> list[str]` where `outcome` is passed as a kwarg. The builder must use `operation="end_work"`, NOT compound operation strings like `"end_work_block"`.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Guidance integration + tag cleanup in one handler, logically coupled |
| Interface clarity | PASS (after refinement) | Ordering, error handling, and re-read now explicit |
| Dependency correctness | PASS (after wiring) | Depends on #986, #987; must be wired via `depends_on: [986, 987]` |
| Module layering | PASS | Changes in `serve/mcp-kanban` server.py, same layer as existing handlers |
| TDD compliance | PASS | Test file specified; flows through test-writer |
| KISS/YAGNI | PASS | Minimal handler changes, 3 sequential steps |
| Premise challenge | PASS | No existing end_work guidance capability |
| Pattern consistency | PASS | Follows sibling #985 pattern (guidance attachment after engine call) |
| Security surface | PASS | No new system boundaries; internal advisory guidance |
| Single domain | PASS | MCP kanban domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `collect_guidance()` raises | Guidance lost | Any | Yes (try/except per R2) | Operation succeeds, empty guidance |
| `engine.edit_task(remove_tags)` fails | Stale `block:user` persists | ValueError/FileNotFoundError | Yes (try/except per R2) | Agent may skip DR unnecessarily |
| TOCTOU between end_work and edit_task | Tag state changed by concurrent agent | N/A | By design (advisory) | Tolerable per parent C1 rebuttal |

### Challenge Results

- Challenger: `reconsider` (confidence 0.45)
- Architect response: REBUTTED C1–C4, PARTIALLY ACCEPTED C5

**C1 rebuttal (before=None crash):** #987's approved AC specifies `before: KanbanTask | None`. Current code is pre-implementation. Dependency chain (#989 depends on #987) ensures the interface is ready.

**C2 rebuttal (operation naming):** #987's approved AC refinement #2 mandates `operation == "end_work"` with outcome kwarg. Compound names are exploratory artifacts.

**C3 rebuttal (ordering creates false DR warnings):** Agent calling `end_work(outcome="block")` creates a NEW block event. Stale `block:user` from prior user-block is irrelevant — agent's block needs DR. Tag removal before guidance is correct.

**C4 rebuttal (archived task):** Tag removal conditioned on `outcome == "block"`. Blocking doesn't archive. Non-issue.

**C5 partial accept:** Added R2 (error resilience AC).

**Blind spot accepted:** Stale `_record_to_task` — addressed in R1 (re-read after tag removal).

### Verdict: APPROVE (after refinement)

### Action Taken: Advanced to todo. Four refinements appended (ordering, error resilience, dependency wiring, interface contract). Orchestrator must wire `depends_on: [986, 987]`

[[2026-04-19]]

## Test-Writer Notes

- Test file: `serve/mcp-kanban/tests/test_guidance_end_work_973.py`
- Classes: `TestFromAC_EndWorkGuidanceIntegration`
- Tests per category: happy 3, edge 1, error 0, boundary 1
- Total: 5 tests
- ruff: clean

**Status: Tests exist and PASS — implementation already shipped in commit `161e4c2d` (builder #973).**

The `end_work` guidance wiring (guidance call + `block:user` tag removal) was implemented as part of the #973 builder commit, which also created the test file. The task entered `todo` without a prior `## Test-Writer Notes` section, indicating the pipeline was not formally traversed for #989 specifically.

AC Coverage:

| AC Line | Test | Status |
|---------|------|--------|
| `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` | `test_block_outcome_returns_dr_guidance` (indirect) | PASS |
| `outcome="block"` → guidance with DR message | `test_block_outcome_returns_dr_guidance` | PASS |
| `outcome="block"` → removes `block:user` tag | `test_block_outcome_removes_block_user_tag_if_present` | PASS |
| `outcome="success"` → commit reminder guidance | `test_success_outcome_returns_commit_guidance` | PASS |
| `outcome="fail"` / `"reject"` → empty guidance | `test_fail_outcome_returns_empty_guidance`, `test_reject_outcome_returns_empty_guidance` | PASS |

Advancing to in-progress — builder will verify tests pass and close the loop.
[[2026-04-19]]

## Builder Notes

**Verification only** — implementation already shipped in commit `161e4c2d` (builder #973).

### Files verified

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — `collect_guidance("end_work", None, task, outcome=outcome)` call at line 351; `block:user` tag removal logic present.
- `serve/mcp-kanban/tests/test_guidance_end_work_973.py` — 5 tests covering all AC outcomes.

### Test results

5 passed, 0 failed — `TestFromAC_EndWorkGuidanceIntegration` (all 5 AC outcomes covered).

### Lint

`ruff check serve/mcp-kanban/` → All checks passed.

### Evidence

| AC Line | Test | Status |
|---------|------|--------|
| `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` | `test_block_outcome_returns_dr_guidance` (indirect) | PASS |
| `outcome="block"` → DR guidance | `test_block_outcome_returns_dr_guidance` | PASS |
| `outcome="block"` → removes `block:user` | `test_block_outcome_removes_block_user_tag_if_present` | PASS |
| `outcome="success"` → commit reminder | `test_success_outcome_returns_commit_guidance` | PASS |
| `outcome="fail"/"reject"` → empty guidance | `test_fail_outcome_returns_empty_guidance`, `test_reject_outcome_returns_empty_guidance` | PASS |
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 5 passed, 0 failed (TestFromAC_EndWorkGuidanceIntegration, all 5 outcomes)

### Lint

- ruff: clean (0 violations, serve/mcp-kanban/src/ + test file)

### Coverage

- owlbear_mcp_kanban.server: 41% (scoped run, expected — other tools tested elsewhere)
- owlbear_mcp_kanban.guidance: 57%
- Note: coverage reflects single test file scope; full suite covers remaining server paths

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` | `test_block_outcome_returns_dr_guidance` (indirect), `test_success_outcome_returns_commit_guidance` (indirect) | Yes — removing the call silences guidance, both tests fail | LAX (compensated) |
| `outcome="block"` → guidance with DR message | `test_block_outcome_returns_dr_guidance` | Yes — `assert "Decision Request" in result.guidance[0]` | COVERED |
| `outcome="block"` → removes `block:user` tag | `test_block_outcome_removes_block_user_tag_if_present` | Yes — `assert "block:user" not in result.tags` | COVERED |
| `outcome="success"` → commit reminder | `test_success_outcome_returns_commit_guidance` | Yes — `assert "commit" in result.guidance[0].lower()` | COVERED |
| `outcome="fail"` / `"reject"` → empty guidance | `test_fail_outcome_returns_empty_guidance`, `test_reject_outcome_returns_empty_guidance` | Yes — exact `== []` assertion | COVERED |
| Integration test per outcome | 5 tests covering all 4 outcomes | Yes | COVERED |

AC1 rated LAX (behavioral coverage only; `before=None` and ordering non-observable from output). However, behavioral tests AC2/AC4 directly compensate: removing the `collect_guidance` call causes both to fail. No `TestBuilderDiscovered` class exists; LAX is noted, not auto-failed, because indirect behavioral coverage is complete.

#### Security Review

- No hardcoded secrets, tokens, or API keys.
- `task_id` passed only to internal `KanbanEngine` calls; no injection vector.
- `contextlib.suppress(Exception)` pattern consistent with pre-existing `edit_task` and `move_task` handlers.
- No new external dependencies.
- `str(exc)` surfaces only ValueError/FileNotFoundError from engine; no credentials or PII in error paths.
- PASS

#### Test Integrity

New file only — no `TestFromAC_*` modifications. All 5 original RED-phase tests preserved. PRESERVED.

#### Test Quality

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Assertion specificity | ADEQUATE | Substring checks on `guidance[0]` + exact `== []` assertions; redundant `len()` guard harmless |
| Negative/error-path coverage | ADEQUATE | fail and reject outcomes explicitly tested with `== []` |
| Manual mutation reasoning | ADEQUATE | Removing `collect_guidance` → guidance empty → 2 tests fail immediately |
| Test independence | STRONG | Each test uses fresh `tmp_path` fixture; no shared mutable state |
| Descriptive names | STRONG | All 5 names fully describe scenario and expected outcome |

No WEAK ratings.

#### Data Safety

**Noted (informational):** `_block_guidance()` in guidance.py returns `[]` when `"block:user" in after.tags`. Implementation ordering (edit_task before `_record_to_task` before `collect_guidance`) is load-bearing: if `edit_task` raises and `contextlib.suppress` fires, `block:user` may survive to the guidance call, silently suppressing DR message. Verified from guidance.py:75–78. Architecture refinement R2 accepts this as tolerable silent failure. No test covers this error path.

#### Test Gap Analysis

**Gap 1 (minor):** `test_block_outcome_removes_block_user_tag_if_present` asserts tag removal but NOT that guidance is still emitted. The combined assertion ("block:user present → removed AND DR guidance present") has no single test. A mutation that skips `collect_guidance` when `edit_task` succeeds would evade this specific test. Partially compensated by `test_block_outcome_returns_dr_guidance` (block without prior `block:user`). Implementation is correct; gap is in test completeness.

**Gap 2 (trivial):** AC1 ordering (collect_guidance called after engine call) not directly verifiable from integration test output. `before=None` parameter unverifiable since `before` is ignored for `end_work` in guidance.py. Structural behavioral compensation sufficient.

#### Builder Process Quality

1 `## Builder Notes` section. Verification-only task (implementation shipped in #973). CLEAN.

### Pass 2 — INFORMATIONAL

- **6.1 Naming mismatch:** Test file is `test_guidance_end_work_973.py` but task is #989. Causes confusion when correlating test files to kanban tasks. Recommend rename in a follow-up cleanup pass.
- **6.3 Combined scenario tightening:** Adding `assert len(result.guidance) > 0` and `assert "Decision Request" in result.guidance[0]` to `test_block_outcome_removes_block_user_tag_if_present` would close Gap 1 in 2 lines.

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` | server.py:351 `task.guidance = collect_guidance("end_work", None, task, outcome=outcome)` | Indirect via AC2/AC4 | PASS |
| `outcome="block"` returns DR guidance | server.py:351 + guidance.py:75-78 + pytest output | `test_block_outcome_returns_dr_guidance` | PASS |
| `outcome="block"` removes `block:user` | server.py:345-349 `edit_task(remove_tags=["block:user"])` + pytest output | `test_block_outcome_removes_block_user_tag_if_present` | PASS |
| `outcome="success"` returns commit reminder | server.py:351 + guidance.py:64 + pytest output | `test_success_outcome_returns_commit_guidance` | PASS |
| `outcome="fail"` / `"reject"` → empty guidance | guidance.py:48-57 (no match → `[]`) + pytest output | `test_fail_outcome_returns_empty_guidance`, `test_reject_outcome_returns_empty_guidance` | PASS |
| Integration test per outcome | 5 tests in TestFromAC_EndWorkGuidanceIntegration | All 5 | PASS |

### Deductions

- AC1 indirect-only coverage: -0.03
- Gap 1 (combined block+block:user scenario not fully asserted): -0.05

### Verdict

Confidence: **0.92** → PASS → advance to docs
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | Yes | N/A — no doc update needed | `end_work` now returns `guidance` field; `.github/copilot-instructions.md` (78 lines) covers only Cockpit API — no MCP kanban tools section; nothing to update |
| 2 | Module docstrings | Yes | Verified accurate | `end_work` docstring correctly describes the operation (release, note, advance, claim release); guidance is advisory return-model output, not a distinct operation. `collect_guidance()` in `guidance.py` has complete accurate docstring. `KanbanTask.guidance` field documented with comment. |
| 3 | External attribution | No | N/A | Research doc confirms all 6 sources are internal codebase |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/end-work-guidance-989.md` exists; linked in task body under `## Research` |

### Files updated

None — no documentation updates required.

### Scratch files cleaned

No `989-*` scratch files found.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `end_work` calls `collect_guidance("end_work", before=None, after=task, outcome=outcome)` | server.py:351 — literal call matches AC signature | PASS |
| `outcome="block"` returns DR guidance | server.py:351 + `test_block_outcome_returns_dr_guidance` asserts `"Decision Request" in guidance[0]` | PASS |
| `outcome="block"` removes `block:user` tag | server.py:347-349 `edit_task(remove_tags=["block:user"])` + `test_block_outcome_removes_block_user_tag_if_present` | PASS |
| `outcome="success"` returns commit reminder | server.py:351 + `test_success_outcome_returns_commit_guidance` asserts `"commit" in guidance[0].lower()` | PASS |
| `outcome="fail"` / `"reject"` → empty guidance | `test_fail_outcome_returns_empty_guidance`, `test_reject_outcome_returns_empty_guidance` assert `== []` | PASS |
| Integration test per outcome | 5 tests in `TestFromAC_EndWorkGuidanceIntegration` covering all 4 outcomes | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all failures in `serve/mcp-knowledge/` — outside task scope; zero mcp-kanban failures)
- ruff: clean (0 violations)

### Architect Quality: 4/5

Specific, testable AC with 4 refinements (ordering, error resilience, dependency wiring, interface contract). Minor gap: AC1 ordering is structural and not directly observable from integration test output, but behavioral coverage compensates.

### Deduction Breakdown

No deductions applied:

- All 6 AC lines have specific code + test evidence
- Lint clean
- AC quality 4/5 (above threshold)
- Reviewer evidence section present and detailed (0.92, PASS)
- Zero task-scope test failures

### Confidence: 1.00

### Action: archive
