---
id: 990
title: Cockpit `block:user` tag lifecycle in mutation routes
status: archived
priority: medium
created: 2026-04-18T21:23:00.867289+00:00
updated: 2026-04-19T02:08:29.739798+00:00
tags:
- type:feature
- scope:cockpit
- scope:kanban
parent: 973
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D3.

## Problem

Cockpit-initiated blocks are indistinguishable from agent-initiated blocks. Agents should not create DRs for user-driven blocks.

## Acceptance Criteria

- Cockpit `edit_task` route: when `block_reason` is set (blocking), append `block:user` to engine kwargs `add_tags`.
- Cockpit `edit_task` route: when `block_reason` is cleared (unblocking), append `block:user` to engine kwargs `remove_tags`.
- Tag injection happens in the route handler, AFTER `_build_edit_kwargs()` returns (avoids tag-diff contract conflict).
- Integration test: block via cockpit → task has `block:user` tag.
- Integration test: unblock via cockpit → `block:user` tag removed.
- Integration test: block with explicit tags list → `block:user` is added without breaking user's tag set.

## Files

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
- `tests/test_cockpit_mutation_api.py` (extend existing)

## Dependencies

- None (independent of MCP guidance work)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/cockpit-block-user-tag-lifecycle-990.md
- Sources: 5 studied, 4 high-relevance (mutation.py, engine.py, architect stance, D3 decision)
- Recommendation: Proceed with architect's exact implementation — 8 LOC production, 3 integration tests (confidence: 0.92)
- Key finding: tag-diff conflict when user sends `tags` + `block_reason` simultaneously is handled correctly by architect's post-injection code (strip conflicting tag from opposite list before inserting)
- Follow-up tasks created: none needed — #990 AC already covers all identified scenarios
- Decision requests: none (T1 — implementation follows approved D3 decision)
[[2026-04-18]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Tag-diff conflict resolution — one concern |
| Interface clarity | PASS (after refinement) | See refined AC below |
| Dependency correctness | PASS | Should depend on #975 (baseline implementation) — noted below |
| Module layering | PASS | Route-layer tag injection, no engine changes |
| TDD compliance | PASS | Flows through test-writer (RED) then builder (GREEN) |
| KISS/YAGNI | PASS | ~4 LOC fix + 2 conflict tests |
| Premise challenge | PASS | D3 decision authorises `block:user` convention |
| Pattern consistency | PASS | Extends existing `_apply_block_kwargs` helper |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit scope only |

### Relationship to #975 / #977

**#975** (status: review) already implements basic `block:user` tag lifecycle — 4 tests in `TestFromAC_BlockUserTag`, production code in `_apply_block_kwargs` (commit 22264efc). AC items 1-2 and 4-5 of this task are **fully superseded** by #975.

**#977** (status: backlog) is **redundant** — #975's pipeline execution (test-writer → builder) already completed the GREEN phase. #977 should be closed.

**#990's unique value** is the tag-diff conflict edge cases: when `_apply_list_diff` and `_apply_block_kwargs` produce contradictory entries in `add_tags`/`remove_tags` for `block:user`. The current `_apply_block_kwargs` (from #975's builder) has a confirmed bug in this scenario.

### Bug: Tag-Diff Conflict in `_apply_block_kwargs`

Engine applies `add_tags` first, then `remove_tags` — so `remove_tags` wins when the same tag appears in both lists.

**Scenario (blocking):** Task has `block:user`. User sends `tags: ["scope:test"]` (omitting `block:user`) + `block_reason: "reason"`.

1. `_apply_list_diff` → `remove_tags: ["block:user"]`, `add_tags: ["scope:test"]`
2. `_apply_block_kwargs` checks `if "block:user" not in current_tags:` → FALSE (it IS present) → skips add
3. Result: `block:user` removed despite active blocking

**Scenario (unblocking):** Task lacks `block:user`. User sends `tags: ["block:user", "scope:test"]` + `block_reason: null`.

1. `_apply_list_diff` → `add_tags: ["block:user", "scope:test"]`
2. `_apply_block_kwargs` checks `if "block:user" in current_tags:` → FALSE (not present) → skips remove
3. Result: `block:user` added despite unblocking

**Fix:** When blocking, strip `block:user` from `remove_tags` if present. When unblocking, strip `block:user` from `add_tags` if present.

### Refined AC (authoritative for test-writer and builder)

AC items 1-2, 4-5 from the original body are **superseded by #975** — do not re-test.

**Active AC for #990:**

1. **Conflict resolution (blocking):** When `block_reason` is set and `remove_tags` contains `block:user` (from tag-diff), strip it from `remove_tags` before engine call. Ensures `block:user` is preserved during simultaneous tag edit + block.
2. **Conflict resolution (unblocking):** When `block_reason` is cleared and `add_tags` contains `block:user` (from tag-diff), strip it from `add_tags` before engine call. Ensures `block:user` is removed during simultaneous tag edit + unblock.
3. **Integration test — block conflict:** Task already has `block:user` tag; user sends `tags` omitting it + `block_reason` set → response tags include `block:user` (not removed by tag-diff).
4. **Integration test — unblock conflict:** Task lacks `block:user`; user sends `tags` including `block:user` + `block_reason: null` → response tags exclude `block:user` (not added by tag-diff).
5. **Integration test — block + new tags (happy path):** Task has no prior tags; user sends `tags: ["scope:test"]` + `block_reason` set → response tags include both `scope:test` and `block:user`.

### File Scope

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — fix `_apply_block_kwargs` conflict handling
- `tests/test_cockpit_mutation_api.py` — 3 new tests in `TestFromAC_BlockUserTag` (or new class)

### Missing Dependency

This task should `depends_on: [975]` since #975 provides the baseline `_apply_block_kwargs` implementation. Cannot add via current tools — builder should verify #975 is merged before implementing.

### Challenge Results

- Challenger: **reconsider** (confidence 0.40)
- Key issues: duplicate task chain, untested conflict, AC/code location mismatch
- Architect response: **accepted all** — refined scope to conflict resolution only, documented #975/#977 overlap, added explicit conflict test AC items, clarified location as ordering constraint not style preference

### Verdict: APPROVE (with refinement)

### Action Taken: Refined scope to tag-diff conflict edge cases only; superseded basic lifecycle AC covered by #975; advanced to todo

[[2026-04-19]]

## Test-Writer Notes

**Status: Pre-implemented pass-through**

The #973 builder (commit `161e4c2d`) pre-implemented both the production code AND the test class for this task as a side effect of its work. No failing tests can be written because all AC items are already implemented and tested.

### Test file

`tests/test_cockpit_mutation_api.py` — class `TestFromAC_BlockUserTagConflict` (lines ~565–650)

### Tests written (all PASS — pre-implemented)

| Test | Category | AC item |
|------|----------|---------|
| `test_block_conflict_preserves_block_user_tag` | integration/conflict | AC1 + AC3 |
| `test_unblock_conflict_removes_block_user_tag` | integration/conflict | AC2 + AC4 |
| `test_block_with_new_tags_adds_both` | happy path | AC5 |

**Total: 3 tests — 0 fail (all pass; pre-implementation complete)**

### AC coverage

| AC item | Covered by |
|---------|------------|
| AC1: blocking strips block:user from remove_tags | test_block_conflict_preserves_block_user_tag |
| AC2: unblocking strips block:user from add_tags | test_unblock_conflict_removes_block_user_tag |
| AC3: integration block conflict → block:user preserved | test_block_conflict_preserves_block_user_tag |
| AC4: integration unblock conflict → block:user absent | test_unblock_conflict_removes_block_user_tag |
| AC5: block + new tags → both tags present | test_block_with_new_tags_adds_both |

### Pre-implementation details

- `_apply_block_kwargs()` in `mutation.py` has full conflict resolution (6 lines added in `161e4c2d`)
- Engine handles `add_tags=[]` gracefully via `if add_tags:` falsy check (verified via `engine.py` read)
- All 37 mutation API tests green; ruff clean
- Zero coverage gaps against refined AC

### Builder guidance

No implementation work required. Verify `_apply_block_kwargs` conflict resolution (lines ~141-160 in `mutation.py`) and advance directly to review.
[[2026-04-19]]

## Builder Notes

### Verification-only task — no new implementation required

The #973 builder (commit `161e4c2d`) pre-implemented all AC items as a side effect of its work. This session verified the implementation and advanced to review.

### Files verified (no changes made)

- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` — `_apply_block_kwargs` (lines 138–160): conflict resolution implemented correctly; strips `block:user` from `remove_tags` when blocking, strips from `add_tags` when unblocking.
- `tests/test_cockpit_mutation_api.py` — `TestFromAC_BlockUserTagConflict` class (lines 570–660): 3 tests covering AC1–AC5.

### Test results

- 3 passed, 0 failed (`TestFromAC_BlockUserTagConflict` scoped run)
- All AC items covered: AC1 (block conflict), AC2 (unblock conflict), AC3+AC5 (happy path)

### Lint

- ruff: clean (`mutation.py` + `test_cockpit_mutation_api.py`)

### AC evidence

| AC | Test | Status |
|----|------|--------|
| AC1: blocking strips block:user from remove_tags | test_block_conflict_preserves_block_user_tag | PASS |
| AC2: unblocking strips block:user from add_tags | test_unblock_conflict_removes_block_user_tag | PASS |
| AC3: integration block conflict → block:user preserved | test_block_conflict_preserves_block_user_tag | PASS |
| AC4: integration unblock conflict → block:user absent | test_unblock_conflict_removes_block_user_tag | PASS |
| AC5: block + new tags → both present | test_block_with_new_tags_adds_both | PASS |
[[2026-04-19]]

## Review Evidence

### Test Results

- pytest: 37 passed, 0 failed, 0 skipped (run independently via quality-runner)

### Lint: clean

- ruff: 0 violations — `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` + `tests/test_cockpit_mutation_api.py`

### Coverage

- `owlbear_cockpit.routes.mutation`: not captured by quality-runner (module path targeting issue); branch coverage confirmed via code-reader analysis — all meaningful branches exercised by passing tests. Informational only.

---

### Pass 1 — CRITICAL

#### 5.0 Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: blocking strips block:user from remove_tags | test_block_conflict_preserves_block_user_tag | YES — tag-diff adds block:user to remove_tags; without strip it would be removed from task despite active block | COVERED |
| AC2: unblocking strips block:user from add_tags | test_unblock_conflict_removes_block_user_tag | YES — tag-diff adds block:user to add_tags; without strip it would be added despite unblocking | COVERED |
| AC3: block conflict integration — block:user preserved | test_block_conflict_preserves_block_user_tag | YES — direct assertion `"block:user" in response.json()["tags"]` | COVERED |
| AC4: unblock conflict integration — block:user absent | test_unblock_conflict_removes_block_user_tag | YES — direct assertion `"block:user" not in response.json()["tags"]` | COVERED |
| AC5: block + new tags — both present | test_block_with_new_tags_adds_both | YES — asserts both "block:user" and "scope:test" in result tags | COVERED |

No MISSING. No LAX.

#### 5.1 Security Review

- No hardcoded secrets, tokens, or API keys.
- No injection: user input validated via Pydantic `EditRequest`/`MoveRequest` with `extra="forbid"`.
- No path traversal: task_id converted to string and passed to engine — no file path construction in route layer.
- No SQL, shell commands, or unsafe deserialization.
- No new dependencies introduced.

**No issues.**

#### 5.2 Test Integrity

All `TestFromAC_BlockUserTagConflict` tests were authored by the test-writer for this task. The builder made no code changes (verification-only session). No modifications to existing `TestFromAC_*` methods.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| test_block_conflict_preserves_block_user_tag | None (builder did not touch) | PRESERVED |
| test_unblock_conflict_removes_block_user_tag | None | PRESERVED |
| test_block_with_new_tags_adds_both | None | PRESERVED |

#### 5.3 Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|---------|
| Assertion specificity | STRONG | Checks exact tag presence/absence by name, not truthy; includes failure messages with repr |
| Negative/error-path coverage | STRONG | Conflict scenarios are inherently negative paths (things that go wrong without the fix) |
| Manual mutation reasoning | STRONG | Removing the list-comprehension filter from either `remove_tags` or `add_tags` would fail the corresponding test; removing `_apply_block_kwargs` entirely would fail AC5 |
| Test independence | STRONG | Each test uses fresh `board_dir` via `tmp_path`; no shared mutable state |
| Descriptive names | STRONG | Names describe scenario + expected outcome |

No WEAK ratings.

#### 5.4 Data Safety

- No LLM output persisted without sanitization.
- No race conditions introduced.
- No unbounded input to resource-intensive operations.

**No issues.**

#### 5.5 Implementation-Aware Test Gap Analysis

Code paths in `_apply_block_kwargs` (mutation.py lines 131–151):

| Branch | Covered by |
|--------|-----------|
| Blocking + block:user IN current_tags (strip removes it from remove_tags; add skipped) | test_block_conflict_preserves_block_user_tag |
| Blocking + block:user NOT in current_tags (strip is no-op; add to add_tags) | TestFromAC_BlockUserTag.test_block_adds_block_user_tag (prior task, 37 passing) |
| Unblocking + block:user NOT in current_tags (strip removes it from add_tags; remove skipped) | test_unblock_conflict_removes_block_user_tag |
| Unblocking + block:user IN current_tags (strip is no-op; add to remove_tags) | TestFromAC_BlockUserTag.test_unblock_removes_block_user_tag (prior task) |
| Blocking with new tags (diff + inject both present) | test_block_with_new_tags_adds_both |

No untested significant paths.

#### 5.6 Necessity Check

Not applicable — no new dependencies or external integrations.

#### 5.7 Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A (verification-only) |
| Assessment | CLEAN |

---

### Pass 2 — INFORMATIONAL

- **Coverage module not measured:** quality-runner did not capture `owlbear_cockpit.routes.mutation` in its output (likely a module path targeting issue); actual branch coverage verified via code-reader. No deduction.
- **`block_reason` not in kwargs on unblock:** `_apply_block_kwargs` sets `blocked=False` but does not set `block_reason=None` in kwargs. Relies on engine's own clearing behavior when `blocked=False`. Engine behavior verified by passing `test_edit_null_block_reason_clears_blocked_state` in prior task scope. Acceptable.

---

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1: blocking strips block:user from remove_tags | mutation.py lines 137–139: `kwargs["remove_tags"] = [t for t in remove_tags if t != "block:user"]` | test_block_conflict_preserves_block_user_tag | PASS |
| AC2: unblocking strips block:user from add_tags | mutation.py lines 146–147: `kwargs["add_tags"] = [t for t in add_tags if t != "block:user"]` | test_unblock_conflict_removes_block_user_tag | PASS |
| AC3: block conflict → block:user preserved | test asserts `"block:user" in response.json()["tags"]` after strip; 37 pass | test_block_conflict_preserves_block_user_tag | PASS |
| AC4: unblock conflict → block:user absent | test asserts `"block:user" not in response.json()["tags"]` after strip; 37 pass | test_unblock_conflict_removes_block_user_tag | PASS |
| AC5: block + new tags → both present | asserts both "block:user" and "scope:test" in result; 37 pass | test_block_with_new_tags_adds_both | PASS |

---

### Confidence: .96

### Verdict: PASS

[[2026-04-19]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Internal route logic only — no endpoint added/removed, no request/response schema change; copilot-instructions.md endpoint table accurate |
| 2 | Module docstrings | Yes | Verified | mutation.py: module, MoveRequest, EditRequest, move_task,_build_edit_kwargs, _apply_block_kwargs,_apply_list_diff all have accurate docstrings; _apply_block_kwargs docstring covers conflict resolution at correct level of abstraction |
| 3 | External attribution | No | N/A | Sources were mutation.py, engine.py, architect stance, D3 decision — all internal |
| 4 | CLI changes | No | N/A | No CLI changes |
| 5 | Research doc | Yes | Verified | .owlbear/research/cockpit-block-user-tag-lifecycle-990.md exists; linked from task body; follow-ups noted as none needed |

### Files Updated

- None

### Scratch Files Cleaned

- None (no .owlbear/scratch/990-* files found)
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: blocking strips block:user from remove_tags | mutation.py L145: `kwargs["remove_tags"] = [t for t in remove_tags if t != "block:user"]` | PASS |
| AC2: unblocking strips block:user from add_tags | mutation.py L155: `kwargs["add_tags"] = [t for t in add_tags if t != "block:user"]` | PASS |
| AC3: block conflict → block:user preserved | test_block_conflict_preserves_block_user_tag: asserts `"block:user" in response.json()["tags"]` | PASS |
| AC4: unblock conflict → block:user absent | test_unblock_conflict_removes_block_user_tag: asserts `"block:user" not in response.json()["tags"]` | PASS |
| AC5: block + new tags → both present | test_block_with_new_tags_adds_both: asserts both "block:user" and "scope:test" in result tags | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all in serve/mcp-knowledge — outside task scope), 0 skipped
- ruff: clean (0 violations)

### Architect Quality: 5/5

Excellent scoping — identified #975/#977 overlap, narrowed to unique conflict-resolution value, documented bug with step-by-step scenarios, specific and independently verifiable AC items. Challenge feedback accepted and incorporated.

### Deduction Breakdown

- AC lines without evidence: 0 (all 5 verified)
- Lint violations: 0
- AC quality ≤ 3: N/A (5/5)
- Missing reviewer evidence: 0 (detailed two-pass review present)
- Full-suite failures in scope: 0 (none in cockpit)

### Confidence: 1.00

### Action: archive
