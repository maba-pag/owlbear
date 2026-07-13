---
id: 986
title: 'Add `guidance: list[str]` field to KanbanTask model'
status: archived
priority: medium
created: 2026-04-18T21:22:36.972344+00:00
updated: 2026-04-19T01:50:16.604409+00:00
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
Parent: #973. Brief: `.owlbear/briefs/draft-blocked-task-dr-enforcement/brief.md`. Decision: D4.

## Problem

`KanbanTask` in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py` has no `guidance` field. This is the foundation for all block-time guidance features.

## Acceptance Criteria

- `guidance: list[str] = Field(default_factory=list)` is the **first declared field** on `KanbanTask` (before `id`).
- Pydantic v2 declaration-order serialization places `guidance` first in JSON output.
- `_record_to_task` continues to work — engine `Task` lacks `guidance`, Pydantic defaults to `[]`.
- Unit test: field exists, defaults to empty list.
- Unit test: JSON serialization order has `guidance` as first key.
- Unit test: `model_validate` from engine Task dict (no guidance key) produces `guidance=[]`.

## Files

- `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- `serve/mcp-kanban/tests/test_guidance_model_973.py` (new)
[[2026-04-18]]

## Research

- Research doc: .owlbear/research/guidance-model-field-986.md
- Sources: 6 studied, 5 high-relevance (≥0.8)
- Recommendation: Proceed with D4 as specified — Pydantic 2.12.5 declaration-order serialization verified empirically; `_record_to_task` auto-fills `guidance=[]`; no downstream breakage (confidence: .95)
- Follow-up tasks created: none (downstream #987/#985/#989/#991 already exist)
- Decision requests: none (D4 locked, T1 autonomous)
[[2026-04-18]]

## Architecture Review

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| `guidance: list[str] = Field(default_factory=list)` first declared field | PASS — verifiable, specific | None |
| Pydantic v2 declaration-order serialization | PASS — research verified empirically | None |
| `_record_to_task` continues to work | PASS — engine `Task` lacks `guidance`, Pydantic defaults `[]` | None |
| Unit test: field exists, defaults to `[]` | PASS — already in `test_guidance.py` L69-73 (#974 RED) | None |
| Unit test: JSON serialization order | PASS — already in `test_guidance.py` L75-82 (#974 RED) | None |
| Unit test: `model_validate` from engine Task dict | PASS — verifiable, net-new test needed | None |
| Files: `test_guidance_model_973.py` (new) | **REFINED** — tests already exist in `test_guidance.py`; creating a second file duplicates logic | Changed to `test_guidance.py` |

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One field addition to one model |
| Interface clarity | PASS | Field type, default, position, serialization order all specified |
| Dependency correctness | PASS | No dependencies; foundation task |
| Module layering | PASS | Only touches `serve/mcp-kanban` models, no upward imports |
| TDD compliance | PASS | Test-writer will add AC6 test to `test_guidance.py` |
| KISS/YAGNI | PASS | Single field with default factory, minimal |
| Premise challenge | PASS | Foundation for D4 guidance feature under #973 |
| Pattern consistency | PASS | Follows existing `tags`/`depends_on` `Field(default_factory=list)` pattern |
| Security surface | PASS | No new system boundary; field populated by internal `collect_guidance`, not user input |
| Single domain | PASS | MCP kanban domain only |

### Observations

1. **Pre-implementation.** The `guidance` field already exists in `models.py` and AC4/AC5 tests already pass in `test_guidance.py` (from #974 RED phase). Net-new work is AC6 (`model_validate` roundtrip test). Test-writer/builder should verify existing tests and add the missing one.
2. **`TaskSummary` gap.** `list_tasks` returns `TaskSummary` (engine model, `extra="ignore"`, no `guidance` field) — guidance is silently dropped on that path. Out of scope for #986 but should be tracked under parent #973 if `list_tasks` consumers need guidance.
3. **Test file.** AC refined: `test_guidance_model_973.py` → `test_guidance.py` (existing file, already contains AC4/AC5 equivalents from #974).

### Challenge Results

- Challenger: reconsider (0.45)
- Key concerns: pre-implementation, missing AC6 test, file naming mismatch, TaskSummary gap
- Architect response: ACCEPTED refinements for file naming. Pre-implementation is a sequencing artifact from #974 RED phase — doesn't invalidate AC. TaskSummary gap noted for #973. AC6 is the key deliverable. Confidence in refined AC: .90.

### Verdict: APPROVE (after refinement)

### Action Taken: Refined test file reference from `test_guidance_model_973.py` to `test_guidance.py`. Approved to `todo`

[[2026-04-19]]

## Test-Writer Notes

- Test file: `serve/mcp-kanban/tests/test_guidance.py`
- Classes: `TestFromAC_KanbanTaskGuidanceField`
- Tests per category: happy 3, edge 0, error 0, boundary 0
- Total: 12 tests in file; AC6 test moved to `TestFromAC_KanbanTaskGuidanceField`
- ruff: clean

**Pre-implementation note:** All tests PASS — implementation was completed ahead of this task as a sequencing artifact from #974 RED/GREEN. The architecture review explicitly acknowledged this (AC4/AC5 tests existed; AC6 was in `TestBuilderDiscovered`). AC6 test `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` moved from `TestBuilderDiscovered` to `TestFromAC_KanbanTaskGuidanceField` per test-writer naming conventions. `TestBuilderDiscovered` class removed (was empty after the move).

AC coverage:

| AC | Test | Status |
|----|------|--------|
| AC4: field exists, defaults to [] | `test_guidance_defaults_to_empty_list` | PASS (pre-impl) |
| AC5: JSON serialization order, guidance first | `test_guidance_is_first_key_in_model_dump` | PASS (pre-impl) |
| AC6: model_validate from engine dict without guidance key → [] | `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` | PASS (pre-impl) |

Commit: `257ea230 test: move AC6 model_validate test to TestFromAC_ class (#986, test-writer)`
[[2026-04-19]]

## Builder Notes

**Files changed:** None — implementation was pre-completed in #974 GREEN phase.

**What was verified:**

- `guidance: list[str] = Field(default_factory=list)` is first declared field on `KanbanTask` in `serve/mcp-kanban/src/owlbear_mcp_kanban/models.py`
- All 3 `TestFromAC_KanbanTaskGuidanceField` tests pass: `test_guidance_defaults_to_empty_list`, `test_guidance_is_first_key_in_model_dump`, `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` (AC6)
- ruff: clean on both model and test files

**Test results:** 3 passed, 0 failed

**Coverage:** AC4 ✅ AC5 ✅ AC6 ✅ — all AC criteria satisfied

**Lint status:** clean

**Evidence:** Pre-implementation artifact from #974 RED/GREEN; test-writer moved AC6 test to `TestFromAC_KanbanTaskGuidanceField` in commit `257ea230`. Builder confirmed GREEN state, no code changes needed.
[[2026-04-19]]

## Review Evidence

### Quality-Runner Report

- pytest: 12 passed, 0 failed, 0 skipped
- lint (ruff): clean, 0 violations
- coverage: 96% on `owlbear_mcp_kanban.models`

### Code-Reader Findings

- `guidance: list[str] = Field(default_factory=list)` confirmed at models.py:14 — first declared field, before `id` at line 17 ✅
- `_record_to_task` at server.py:158–160 uses `KanbanTask.model_validate(record.model_dump())` — guidance defaults to `[]` when absent ✅
- `TestBuilderDiscovered` class removed from test file ✅
- AC6 test relocated into `TestFromAC_KanbanTaskGuidanceField` (strengthened, not weakened) ✅
- Security: `guidance` populated only via internal `collect_guidance()` — not reachable from user input ✅

### AC Compliance Table

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `guidance` first declared field (before `id`) | models.py:14 | `test_guidance_defaults_to_empty_list` | PASS |
| Pydantic v2 serialization order: guidance first | field order + passing tests | `test_guidance_is_first_key_in_model_dump` | PASS |
| `_record_to_task` works with no guidance key | server.py:158–160 model_validate | `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` | PASS |
| Unit test: field defaults to `[]` | 12/12 pass | `test_guidance_defaults_to_empty_list` | PASS |
| Unit test: JSON serialization order | 12/12 pass | `test_guidance_is_first_key_in_model_dump` | PASS |
| Unit test: model_validate from engine dict → `[]` | 12/12 pass | `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` | PASS |

### Pass 1 Critical Checks

- 5.0 AC coverage: all 3 AC tests present in `TestFromAC_KanbanTaskGuidanceField`, all COVERED
- 5.1 Security: no OWASP issues — guidance is internal-only
- 5.2 TestFromAC integrity: AC6 test STRENGTHENED (moved from `TestBuilderDiscovered` → `TestFromAC_`)
- 5.3 Test quality: all assertions STRONG (direct equality, include error messages)
- 5.4 Data safety: no issues
- 5.5 Code path coverage: 96% on simple model, no untested branches
- 5.7 Builder process: CLEAN (1 notes section)

### Deductions: 0

### Verdict: PASS | confidence .97

[[2026-04-19]]

## Docs Gate

| # | Item | Applies? | Status | Evidence |
|---|------|----------|--------|----------|
| 1 | Behavior/API — copilot-instructions.md | No | N/A | `guidance` is an internal MCP model field; copilot-instructions.md documents Cockpit endpoints, not mcp-kanban model fields |
| 2 | Module docstrings | Yes | Pass | `KanbanTask` class docstring accurate; `_coerce_claimed` docstring untouched; new field has inline comment — no gaps |
| 3 | External attribution | No | N/A | Research used only empirical Pydantic verification and codebase files; no external URLs to attribute |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Pass | `.owlbear/research/guidance-model-field-986.md` exists and is linked from task body; follow-up tasks (#987/#985/#989/#991) confirmed existing |
| 6 | No impact | — | — | Items 1,3,4 N/A; items 2,5 verified clean |

**Files updated:** None — no documentation changes required.

**Scratch files cleaned:** No `986-*` scratch files found.
[[2026-04-19]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| `guidance` first declared field (before `id`) | models.py:15, `id` at line 18 | PASS |
| Pydantic v2 serialization order: guidance first | `test_guidance_is_first_key_in_model_dump` passes | PASS |
| `_record_to_task` works with no guidance key | Reviewer: server.py:158-160 + AC6 test | PASS |
| Unit test: field defaults to [] | `test_guidance_defaults_to_empty_list` PASS | PASS |
| Unit test: JSON serialization order | `test_guidance_is_first_key_in_model_dump` PASS | PASS |
| Unit test: model_validate from engine dict | `test_model_validate_from_engine_dict_without_guidance_gives_empty_list` PASS | PASS |

### Test Results

- pytest: 658 passed, 6 failed (all mcp-knowledge scope, not task scope), 0 skipped
- ruff: clean, 0 violations
- owlbear_mcp_kanban.models coverage: 100%

### Architect Quality: 5/5

All 6 AC lines specific, verifiable, testable. Only refinement: test file naming (minor). Clean implementation path.

### Deduction Breakdown

No deductions applied. All AC lines have specific evidence. Lint clean. AC quality 5/5. Reviewer evidence detailed with PASS at .97. No in-scope test failures.

### Confidence: 1.00

### Action: archive
