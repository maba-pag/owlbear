---
id: 704
title: 'Tests: graph builder and inter-doc builder async extractor migration'
status: archived
priority: medium
created: 2026-04-09T00:55:49.1829555+02:00
updated: 2026-04-10T01:47:50.870268+02:00
started: 2026-04-10T01:47:50.870268+02:00
completed: 2026-04-10T01:47:50.870268+02:00
tags:
    - scope:knowledge
    - ' type:test'
parent: 676
depends_on:
    - 687
blocked: true
block_reason: 'Superseded by #687 — all AC items either completed or impossible. Recommend archival.'
class: standard
---

## Context
TDD RED phase for graph builder async migration. After #687 makes `StructuredExtractor.extract()` async, the graph builders (`graph_builder.py`, `inter_doc_graph_builder.py`) still call `self._extractor.extract(prompt)` without `await`. Their test helper `_make_mock_extractor()` uses sync `MagicMock(spec=StructuredExtractor)`. Tests must be updated to use `AsyncMock` so they fail against the un-awaited production code.

Identified by reviewer of #676 — decomposition gap in the original plan.

## Acceptance Criteria

- [ ] AC1: `_make_mock_extractor()` in `tests/test_graph_builder.py` returns an `AsyncMock` with `extract` as an async callable returning `ExtractionResult`
- [ ] AC2: `_make_mock_extractor()` in `tests/test_inter_doc_graph_builder.py` returns an `AsyncMock` with `extract` as an async callable returning `ExtractionResult`
- [ ] AC3: All tests in `TestFromAC_IntraDocGraphBuilder` that exercise the extractor FAIL — `graph_builder.py` line 122/130 calls `self._extractor.extract(prompt)` without `await`, receiving a coroutine instead of `ExtractionResult`
- [ ] AC4: All tests in `TestFromAC_InterDocGraphBuilder` that exercise the extractor FAIL — `inter_doc_graph_builder.py` line 154 calls `self._extractor.extract(prompt)` without `await`
- [ ] AC5: Guard tests (extractor=None, <2 entities) continue to PASS — extractor is never called

## Affected Files
- tests/test_graph_builder.py (modify `_make_mock_extractor()`)
- tests/test_inter_doc_graph_builder.py (modify `_make_mock_extractor()`)

[[2026-04-09]] Thu 08:04
## Architecture Review

### Verdict: REJECT — Task Superseded by #687

### Finding: Premise Invalidated

Task #704 was created during #676's cycle-2 architecture review to close a decomposition gap: graph builder test files needed AsyncMock migration for the upcoming async StructuredExtractor protocol change.

However, #687's architect independently expanded #687's scope (AC3-AC7 in #687's refined AC) to include the same graph builder changes. #687's pipeline then completed the full work:

| #704 AC | #687 Deliverable | Status |
|---------|-------------------|--------|
| AC1: `_make_mock_extractor()` in test_graph_builder.py returns AsyncMock | #687 test-writer added `_make_async_mock_extractor()` (L45); original `_make_mock_extractor()` auto-converts via spec (MagicMock(spec=StructuredExtractor) where extract is now `async def`) | SUPERSEDED |
| AC2: Same in test_inter_doc_graph_builder.py | Same pattern — `_make_async_mock_extractor()` at L49; spec auto-conversion applies | SUPERSEDED |
| AC3: TestFromAC_IntraDocGraphBuilder tests FAIL (no await at L122/130) | graph_builder.py L122, L130 already have `await` (committed f6cff3f). Tests PASS. IMPOSSIBLE to satisfy. | IMPOSSIBLE |
| AC4: TestFromAC_InterDocGraphBuilder tests FAIL (no await at L154) | inter_doc_graph_builder.py L154 already has `await` (committed f6cff3f). Tests PASS. IMPOSSIBLE to satisfy. | IMPOSSIBLE |
| AC5: Guard tests pass (extractor=None, less than 2 entities) | Already PASS — unaffected by either task | MOOT |

### Codebase Evidence

- Production code: `await self._extractor.extract(prompt)` confirmed at graph_builder.py:122, graph_builder.py:130, inter_doc_graph_builder.py:154
- Test helpers: `_make_async_mock_extractor()` exists in both test files (added by #687 test-writer)
- Test classes: `TestFromAC_IntraDocAsyncExtractorAwait` (5 tests) and `TestFromAC_InterDocAsyncExtractorAwait` (4 tests) already exist and pass
- #687 status: `done` (reviewed at confidence 0.95, committed f6cff3f)

### Root Cause

Timeline collision: the #676 architect created #704/#705 to fix a decomposition gap, then the #687 architect expanded #687's AC to cover the same files. Both acted correctly given their local context — but the scope expansion in #687 made #704 and #705 redundant before they were dispatched.

### Companion Task #705

#705 ("Update graph builders to await async StructuredExtractor.extract()") is also superseded for the same reason — its AC1/AC2 (add `await` to graph_builder.py L122/130 and inter_doc_graph_builder.py L154) are already done by #687's builder. Should be rejected in a follow-up cycle.

### Evaluation (abbreviated — task is obsolete)

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | Work already completed by #687's expanded scope |
| All other criteria | N/A | Task cannot proceed — AC3/AC4 impossible |

### Challenge Results
- Challenger: SKIP (REJECT verdict — challenger not required)

### Action Taken
Rejected to research. Companion #705 flagged for same treatment. Recommend archiving both as superseded.

[[2026-04-09]] Thu 08:18
## Research

**Verdict: SUPERSEDED — recommend immediate archival**

### Verification

Independently verified all 7 claims from the architecture review against current codebase state. Every claim holds:

| #704 AC | Current State | Evidence |
|---------|---------------|---------|
| AC1: AsyncMock in test_graph_builder.py | `_make_async_mock_extractor()` at L45 (added by #687) | SUPERSEDED |
| AC2: AsyncMock in test_inter_doc_graph_builder.py | `_make_async_mock_extractor()` at L49 (added by #687) | SUPERSEDED |
| AC3: Tests FAIL (no await at L122/130) | `await` already present (grep confirmed) — tests PASS | IMPOSSIBLE |
| AC4: Tests FAIL (no await at L154) | `await` already present (grep confirmed) — tests PASS | IMPOSSIBLE |
| AC5: Guard tests pass | Unaffected | MOOT |

- #687 status: `archived` (completed, reviewed at 0.95, committed f6cff3f)
- Test classes: `TestFromAC_IntraDocAsyncExtractorAwait` (5 tests) and `TestFromAC_InterDocAsyncExtractorAwait` (4 tests) exist and pass

### Root Cause
Timeline collision: #676 architect created #704/#705 to fix a decomposition gap, then #687 architect independently expanded #687's scope to cover the same files. Both acted correctly; the scope expansion made #704/#705 redundant.

### Tier Classification
T1 — Autonomous (cleanup of obsolete task)

### Companion Task #705
#705 is in `backlog`, also superseded by #687. Its AC1/AC2 (add `await` to graph_builder.py:122,130 and inter_doc_graph_builder.py:154) are already done. Recommend archiving #705 as well.

### Follow-up Tasks
None created — no actionable work remains. Both #704 and #705 should be archived as superseded.

### Decision Requests
None — T1 autonomous finding.

## Challenge Results
- Challenger: SKIP — no recommendation to challenge (task is obsolete, verification-only)
- Confidence in superseded verdict: .95

[[2026-04-09]] Thu 08:34
## Architecture Review (Cycle 2)

### Verdict: BLOCK — Superseded, Recommend Archival

This is the second architecture review. Cycle 1 rejected to research; research confirmed all 5 AC items are either SUPERSEDED (AC1/AC2 — async mock helpers already exist) or IMPOSSIBLE (AC3/AC4 — production code already has `await`, tests pass). No new information can change this.

Blocking to prevent infinite reject→research→backlog loop. Orchestrator should archive this task and companion #705.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | All work completed by #687 (archived, commit f6cff3f). AC3/AC4 are impossible to satisfy. |
| All other criteria | N/A | Task has no actionable work remaining |

### Challenge Results
- Challenger: SKIP (BLOCK verdict — task is obsolete)

### Action Taken
Blocked with recommendation to archive. Companion #705 should receive identical treatment.
