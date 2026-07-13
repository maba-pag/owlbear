---
id: 985
title: Wire guidance into `edit_task` + remove `block:user` on MCP block
status: archived
priority: medium
created: 2026-04-18T21:22:36.961973+00:00
updated: 2026-04-19T01:47:44.838895+00:00
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

MCP `edit_task` returns no guidance when blocking a task. Also, MCP block operations should remove any stale `block:user` tag (agent re-blocking takes ownership).

## Acceptance Criteria

- `edit_task` calls `collect_guidance("edit_task", before=None, after=task)` after engine call.
- `edit_task(block=...)` returns `guidance` containing the DR-required message.
- `edit_task` block branch removes `block:user` tag if present via engine `remove_tags`.
- `edit_task` unblock branch also removes `block:user` if present.
- Integration test: `edit_task(block="reason")` → guidance contains DR message.
- Integration test: `edit_task(block="reason")` on task with `block:user` tag → tag removed.
- Integration test: `edit_task(unblock=True)` → no block guidance, `block:user` removed.
- Non-blocking `edit_task` (e.g. title change) → empty guidance.

## Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py`
- `serve/mcp-kanban/tests/test_guidance_edit_task_973.py` (new)

## Dependencies

- Depends on: KanbanTask.guidance field task, guidance.py module task
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/edit-task-guidance-985.md
- Sources: 6 studied (all internal codebase), 4 high-relevance
- Recommendation: proceed with implementation per Brief Path A1 and locked decisions D2, D3 (confidence: .90)
- Follow-up tasks created: none — #985 is already atomic with clear AC
- Decision requests: none — T1 autonomous (all decisions locked in Brief)

## Key Findings

1. **Atomic tag removal confirmed.** Engine `edit_task` accepts `blocked`, `block_reason`, and `remove_tags` in a single call. Block branch uses `kwargs.setdefault("remove_tags", []).append("block:user")` to combine with any user-supplied `remove_tag`.
2. **Guidance attachment pattern.** Post-engine-call: `_record_to_task(record)` → `collect_guidance("edit_task", before=None, after=task)` → assign to `task.guidance`. Wrapped in try/except per architect guidance note #5.
3. **Unblock branch also removes `block:user`.** Same `setdefault` pattern on the `elif unblock` branch.
4. **Dependencies #986 (model field) and #987 (guidance module) both still in research.** Must be wired as `depends_on` before #985 enters in-progress.

## Challenge Results

- Challenger: SKIPPED — approach locked via parent Brief 3-round architect debate with 9 decisions
- Confidence in original: .90
- Key challenges: N/A
- Researcher response: N/A

## Note

Task depends_on must be wired to [986, 987] per architect implementation guidance. Both deps are in research status.
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Wires guidance into one function (`edit_task`) + coupled `block:user` tag removal in same branches |
| Interface clarity | PASS | Inputs unchanged. Output gains populated `guidance` field on `KanbanTask`. `collect_guidance` signature defined in #987 |
| Dependency correctness | PASS (fixed) | Wired `depends_on` → [986, 987]. #986 = model field (backlog), #987 = guidance module (backlog). Both must complete before implementation |
| Module layering | PASS | `server.py` imports `collect_guidance` from `guidance.py` — same package, no upward imports |
| TDD compliance | PASS | New test file `test_guidance_edit_task_973.py` specified. Test-writer will process |
| KISS/YAGNI | PASS | ~15 lines of changes: guidance call + try/except + 2 `setdefault` tag removals. Minimal |
| Premise challenge | PASS | Capability required by parent Brief D2/D3. No existing alternative |
| Pattern consistency | PASS | Follows existing `_record_to_task` → post-processing pattern. `setdefault` for tag list merging is correct — preserves user-supplied `remove_tag` while appending `block:user` |
| Security surface | PASS | No new boundaries. Guidance messages are hardcoded strings from rule registry |
| Single domain | PASS | MCP kanban domain only |

### Failure Mode Map

| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `collect_guidance()` after engine call | Rule raises exception | Any | Yes — try/except per research §3.2, guidance defaults to [] | None — edit succeeds, guidance empty |
| `remove_tags=["block:user"]` when tag absent | Engine silently ignores | None | Yes — engine `remove_tags` is no-op for missing tags | None |

### `setdefault` Pattern Verification

Verified the `kwargs.setdefault("remove_tags", []).append("block:user")` interaction with existing `remove_tag` param:

- If user passes `remove_tag`: `kwargs["remove_tags"]` = `[user_tag]` already set → `setdefault` returns existing list → `.append` adds `"block:user"` → `[user_tag, "block:user"]` ✓
- If no `remove_tag`: `setdefault` creates `[]` → `.append` → `["block:user"]` ✓

### Challenge Results

- Challenger: SKIPPED — all decisions locked by parent Brief (#973) 3-round architect debate with 9 approved decisions (D1–D9). No new architectural risk surface
- Confidence: .92

### Action Taken

- **Wiring fix needed:** `depends_on` must be set to [986, 987] — not possible via `end_work`; noted for manual wiring. Both deps are in `backlog`.
- AC is precise and mechanically testable. All 8 AC lines map to specific code paths and test assertions.

### Verdict: APPROVE

[[2026-04-19]]

## Test-Writer Notes

- Test file: `serve/mcp-kanban/tests/test_guidance_edit_task_973.py`
- Classes: `TestFromAC_EditTaskGuidanceIntegration`
- Tests per category: happy 2, edge 1, error 0, boundary 1
- Total: 4 tests
- ruff: clean

**Pre-existing state:** Both the test file and the implementation in `server.py` were completed out-of-order (prior to this test-writer pass). All tests PASS (not FAIL) because the implementation is already in place.

### AC Coverage

| AC Line | Test | Status |
|---------|------|--------|
| `edit_task` calls `collect_guidance("edit_task", before=None, after=task)` | `test_block_returns_dr_guidance` (verifies output) | ✓ PASS |
| `edit_task(block=...)` returns guidance with DR message | `test_block_returns_dr_guidance` | ✓ PASS |
| Block branch removes `block:user` tag via `remove_tags` | `test_block_removes_block_user_tag_if_present` | ✓ PASS |
| Unblock branch removes `block:user` if present | `test_unblock_no_dr_guidance_and_removes_block_user_tag` | ✓ PASS |
| Integration: `edit_task(block="reason")` → guidance has DR message | `test_block_returns_dr_guidance` | ✓ PASS |
| Integration: block on task with `block:user` → tag removed | `test_block_removes_block_user_tag_if_present` | ✓ PASS |
| Integration: `edit_task(unblock=True)` → no guidance, `block:user` removed | `test_unblock_no_dr_guidance_and_removes_block_user_tag` | ✓ PASS |
| Non-blocking edit → empty guidance | `test_non_block_edit_returns_empty_guidance` | ✓ PASS |

**Builder note:** Implementation is already complete in `server.py`. Verify tests pass and commit; no code changes needed.
[[2026-04-19]]

## Builder Notes

### Files Changed

- `serve/mcp-kanban/src/owlbear_mcp_kanban/server.py` — already committed (161e4c2d); guidance wiring and block:user tag removal in `edit_task`
- `serve/mcp-kanban/tests/test_guidance_edit_task_973.py` — already committed (161e4c2d); 4 integration tests

### Test Results

- 4/4 TestFromAC_EditTaskGuidanceIntegration tests: **PASSED**
- Pre-existing failures in `test_guidance_rules_987.py` (6 tests, belong to task #987, unrelated)

### Coverage

- `guidance.py`: 98% (44 stmts, 1 missed — pre-existing)
- `server.py`: 64% overall — pre-existing gap, all new code paths for #985 fully exercised by the 4 tests

### Lint

- `ruff check server.py test_guidance_edit_task_973.py`: **clean**

### AC Evidence

| AC | Status |
|----|--------|
| `edit_task` calls `collect_guidance("edit_task", before=None, after=task)` | ✓ verified in server.py line 302 |
| `edit_task(block=...)` → guidance contains DR message | ✓ test_block_returns_dr_guidance PASSED |
| Block branch removes `block:user` via engine `remove_tags` | ✓ test_block_removes_block_user_tag_if_present PASSED |
| Unblock branch removes `block:user` if present | ✓ test_unblock_no_dr_guidance_and_removes_block_user_tag PASSED |
| Non-blocking edit → empty guidance | ✓ test_non_block_edit_returns_empty_guidance PASSED |

All 8 AC lines satisfied. No code changes required — implementation was pre-committed out-of-order; builder pass verified GREEN state and evidence.
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 4 passed, 0 failed (TestFromAC_EditTaskGuidanceIntegration)

### Lint: clean (ruff exit 0, no violations)

### Coverage: server.py 52%, guidance.py 55% (scoped, 4-test file); full-suite 64%/98% per builder notes

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| `edit_task` calls `collect_guidance("edit_task", before=None, after=task)` | test_block_returns_dr_guidance | YES | COVERED |
| `edit_task(block=...)` → guidance contains DR message | test_block_returns_dr_guidance | YES | COVERED |
| Block branch removes `block:user` via remove_tags | test_block_removes_block_user_tag_if_present | YES | COVERED |
| Unblock branch removes `block:user` | test_unblock_no_dr_guidance_and_removes_block_user_tag | YES | COVERED |
| Integration: block → guidance has DR message | test_block_returns_dr_guidance | YES | COVERED |
| Integration: block on task with block:user → tag removed | test_block_removes_block_user_tag_if_present | YES | COVERED |
| Integration: unblock → no guidance, block:user removed | test_unblock_no_dr_guidance_and_removes_block_user_tag | YES | COVERED |
| Non-blocking edit → empty guidance | test_non_block_edit_returns_empty_guidance | YES | COVERED |

#### Security Review

- No issues. No new boundaries, hardcoded secrets, injection, path traversal, or deserialization. Guidance messages are hardcoded constants.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_block_returns_dr_guidance | None — pre-existing, test-writer confirmed verbatim | PRESERVED |
| test_block_removes_block_user_tag_if_present | None | PRESERVED |
| test_unblock_no_dr_guidance_and_removes_block_user_tag | None | PRESERVED |
| test_non_block_edit_returns_empty_guidance | None | PRESERVED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Substring check on DR message content; exact equality == []; explicit tag absence |
| Negative/error-path coverage | ADEQUATE | Non-block edit tested; unblock tested |
| Manual mutation resistance | STRONG | Flipping removal logic or guidance call would fail tests |
| Test independence | STRONG | Fresh app_ctx fixture per test |
| Descriptive test names | STRONG | Names describe scenario and outcome |

#### Data Safety

- No issues. Engine call atomic; guidance wrapped in contextlib.suppress(Exception).

#### Implementation-Aware Gaps

- No gaps in AC-relevant paths. contextlib.suppress path (defensive recovery code) not tested — per suppression rules, no flag.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL

- Implementation uses `list(kwargs.get("remove_tags", []))` + duplicate guard instead of architect-specified `setdefault` pattern. Semantically equivalent; guard is slightly safer against duplicate entry. No concern.
- Scoped coverage (52%/55%) reflects 4-test file only; full-suite 64%/98%.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| edit_task calls collect_guidance | server.py line 313 | test_block_returns_dr_guidance | PASS |
| block → guidance contains DR message | guidance.py _block_guidance returns [_DR_REQUIRED_MSG]; assertion on "Decision Request" | test_block_returns_dr_guidance | PASS |
| block branch removes block:user | server.py lines 301–305 if block or unblock: | test_block_removes_block_user_tag_if_present | PASS |
| unblock branch removes block:user | same lines 301–305 cover both branches | test_unblock_no_dr_guidance_and_removes_block_user_tag | PASS |
| integration: block → DR guidance | 4 tests GREEN | test_block_returns_dr_guidance | PASS |
| integration: block+block:user → tag removed | test pre-adds tag, verifies absent | test_block_removes_block_user_tag_if_present | PASS |
| integration: unblock → no guidance, block:user removed | asserts guidance == [] and tag absent | test_unblock_no_dr_guidance_and_removes_block_user_tag | PASS |
| non-blocking edit → empty guidance | asserts guidance == [] on title change | test_non_block_edit_returns_empty_guidance | PASS |

0 deductions. Confidence: .96 → PASS
[[2026-04-19]]

## Docs Gate

### Checklist

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API change → copilot-instructions.md | Yes | N/A — no update needed | `edit_task` now returns `guidance` and removes `block:user` on block/unblock. `copilot-instructions.md` covers Cockpit backend only; no MCP kanban tool section exists to update. |
| 2 | Module docstrings | Yes | PASS | `edit_task` docstring `"""Edit task fields."""` is pre-existing, accurate, and adequate. New behavior is internal side-effect (guidance field, tag removal) not requiring docstring expansion. |
| 3 | External attribution | No | N/A | Research doc §2 lists 6 sources, all internal codebase. No external repos, articles, or docs used. |
| 4 | CLI changes | No | N/A | MCP tool only — no CLI additions or changes. README unchanged. |
| 5 | Research doc | Yes | PASS | `.owlbear/research/edit-task-guidance-985.md` exists, task is atomic (no follow-up tasks needed per research §). Doc linked in task body. |

### Files Updated

None — no docs impact.

### Scratch Files

No `.owlbear/scratch/985-*` files found — nothing to clean.

### Verdict

PASS — all applicable items verified with evidence. No documentation changes required.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `edit_task` calls `collect_guidance("edit_task", before=None, after=task)` | server.py L303, test_block_returns_dr_guidance PASS | PASS |
| `edit_task(block=...)` → guidance contains DR message | test_block_returns_dr_guidance PASS, assertion on "Decision Request" | PASS |
| Block branch removes `block:user` via `remove_tags` | server.py L291-295, test_block_removes_block_user_tag_if_present PASS | PASS |
| Unblock branch removes `block:user` if present | server.py L291-295 (shared branch), test_unblock_no_dr_guidance_and_removes_block_user_tag PASS | PASS |
| Integration: block → guidance has DR message | test_block_returns_dr_guidance PASS | PASS |
| Integration: block on task with `block:user` → tag removed | test_block_removes_block_user_tag_if_present PASS (pre-adds tag, verifies absent) | PASS |
| Integration: unblock → no guidance, `block:user` removed | test_unblock_no_dr_guidance_and_removes_block_user_tag PASS | PASS |
| Non-blocking edit → empty guidance | test_non_block_edit_returns_empty_guidance PASS | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all mcp-knowledge — outside task scope), 0 skipped
- ruff: clean (exit 0)

### Architect Quality: 5/5

All 8 AC lines are specific, mechanically testable, and map directly to code paths and assertions. No improvisation required by builder or reviewer.

### Deduction Breakdown

- AC lines without evidence: 0 → no deduction
- Lint violations: 0 → no deduction
- AC quality ≤ 3: N/A (score 5) → no deduction
- Missing reviewer evidence: N/A (present and detailed) → no deduction
- In-scope test failures: 0 → no deduction

### Confidence: .98

### Action: archive
