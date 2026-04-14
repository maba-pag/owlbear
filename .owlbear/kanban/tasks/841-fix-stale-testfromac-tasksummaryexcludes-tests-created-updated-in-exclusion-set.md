---
id: 841
title: Fix stale TestFromAC_TaskSummaryExcludes tests (created/updated in exclusion
  set)
status: archived
priority: needed
created: '2026-04-12T15:36:21.009577Z'
updated: '2026-04-14T15:13:40.313206+00:00'
tags:
- type:test
- scope:mcp-kanban
parent: null
depends_on:
- 851
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
started: '2026-04-14T10:53:16.4977092+02:00'
completed: '2026-04-14T10:53:16.4977092+02:00'
---

## Acceptance Criteria

- `_EXCLUSION_FIELDS` in `test_tasksummary_model_801.py` removes `created` and `updated` (TaskSummary intentionally includes timestamps per model docstring)
- `test_excluded_fields_absent_from_schema` passes — exclusion set is `{"body", "claimed_by", "claimed_at", "file"}` only
- `test_temporal_fields_not_in_construction_output` is removed or rewritten to assert `created` and `updated` ARE present in `model_dump()` (matching actual model intent)
- Module-level docstring AC2 comment corrected to reflect actual exclusion set
- All `TestFromAC_TaskSummaryExcludes` tests pass after fix
- No other tests regress

## Context

Root cause: TaskSummary model (serve/kanban/src/owlbear_kanban/models.py:90-114) includes `created` and `updated` fields by design (docstring: "excludes body and claimed_by"). Tests written for task #801 incorrectly listed timestamps in `_EXCLUSION_FIELDS`.

Same root cause as #851 but different file/class scope.

File: `tests/test_tasksummary_model_801.py` (lines 60-160)
[[2026-04-12]]
Claimed in error — start_work returned a different backlog task (Fix stale TestFromAC_TaskSummaryExcludes / depends_on:[851]) instead of the expected review task (RED — Tests for BrowserContentFetcher + HttpxContentFetcher). Task left in backlog unchanged. Review proceeding via parent #830 which contains full build history and context.
[[2026-04-13]]
Claimed in error again — start_work returned the wrong task (backlog Fix stale TestFromAC_TaskSummaryExcludes). Releasing claim. Reviewer will proceed with the review-status #841 (RED — Tests for BrowserContentFetcher + HttpxContentFetcher) via direct task body from list_tasks.
[[2026-04-13]]
Claimed in error again — start_work returns backlog task 'Fix stale TestFromAC_TaskSummaryExcludes' instead of review task 'RED — Tests for BrowserContentFetcher + HttpxContentFetcher'. Known ID collision. Releasing claim; reviewer searching by title to locate actual review task.
[[2026-04-13]]
## Architecture Review

### Verdict: REJECT — premise invalid, all tests already pass

### Findings

The task's root cause analysis misquotes the TaskSummary docstring. The task claims the docstring says "excludes body and claimed_by" (implying created/updated should be included). The actual docstring (models.py:91-96) reads:

> Excludes ``body``, ``claimed_by``, ``created``, and ``updated`` from the full Task schema.

The model uses `extra="ignore"` (ConfigDict) and does NOT declare `created` or `updated` fields — they are intentionally excluded. The test file's `_EXCLUSION_FIELDS = {"body", "created", "updated", "claimed_by", "claimed_at", "file"}` correctly reflects the model's design.

### Evidence
- **All 14 tests pass** in `tests/test_tasksummary_model_801.py` — no stale tests exist
- **Dependency #851** (Fix stale ListTasks migration tests) is `done` — sibling fix completed
- **Model docstring** explicitly lists `created` and `updated` as excluded fields
- **Implementing the AC would break correct tests** — `test_excluded_fields_absent_from_schema` and `test_temporal_fields_not_in_construction_output` are correct as-is

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | Model excludes created/updated by design; task AC contradicts actual model |

### Action Taken
Rejected to research. The task's root cause analysis was incorrect — no test fix is needed. If there is a genuine desire to ADD timestamps to TaskSummary, that would be a feature change requiring a new task with updated model AC, not a test fix.
[[2026-04-13]]
## Research
- Research doc: .owlbear/research/stale-tasksummary-excludes-841.md
- Sources: 5 studied, 4 high-relevance
- Finding: **Premise invalid — no fix needed** (confidence: 0.95)
- The task's root cause analysis misquoted the TaskSummary docstring. Actual docstring: "Excludes body, claimed_by, created, and updated." The model does NOT declare `created`/`updated` fields; `extra="ignore"` drops them silently.
- `_EXCLUSION_FIELDS` in `test_tasksummary_model_801.py` is correct as-is. All 14 tests pass.
- Implementing the AC would break currently-passing, correct tests.
- Sibling dependency #851 (stale ListTasks tests) is done.
- Follow-up tasks created: none (no action required)
- Decision requests: none
- Tier: T1 — no action required

## Challenge Results
- Challenger: SKIPPED — factual verification, no competing options
- Confidence in original: 0.95
- Key challenges: n/a
- Researcher response: n/a

## Recommendation
Close this task as invalid. No code changes needed.
[[2026-04-13]]
Claimed in error by reviewer agent. Task is in `backlog` status — reviewer only processes `review`-status tasks. Releasing claim. No changes made.
[[2026-04-13]]
Reviewer boundary check: task is in `backlog` status — reviewer only processes `review`-status tasks. Releasing claim without action.
[[2026-04-13]]
Claimed in error — start_work returned backlog task 'Fix stale TestFromAC_TaskSummaryExcludes' (known ID collision). Releasing claim. Reviewer will inspect kanban task files directly to locate the review-status task and its AC.
[[2026-04-13]]
Claimed in error again — start_work returned backlog task 'Fix stale TestFromAC_TaskSummaryExcludes' (known ID collision). Releasing claim. Reviewer will find correct task via title search.
[[2026-04-13]]
Claimed in error — start_work returned backlog task 'Fix stale TestFromAC_TaskSummaryExcludes' instead of review task 'RED — Tests for BrowserContentFetcher + HttpxContentFetcher'. Known ID collision. Releasing claim without action.
[[2026-04-13]]
## Architecture Review (2nd cycle)

### Verdict: REJECT — premise invalid, confirmed by prior review and research

### Re-verification
Re-checked both source files against the AC:
- **Model docstring** (models.py:91–96): "Excludes ``body``, ``claimed_by``, ``created``, and ``updated``" — unchanged
- **Test file** `_EXCLUSION_FIELDS` (test_tasksummary_model_801.py:61–67): `{"body", "created", "updated", "claimed_by", "claimed_at", "file"}` — correct per model design
- **Model fields**: `TaskSummary` does NOT declare `created` or `updated`; `extra="ignore"` silently drops them
- **Dependency #851**: archived (done)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | AC contradicts the actual model — `created`/`updated` are intentionally excluded. Implementing AC would break correct tests. |

### Challenge Results
- Challenger: SKIPPED — factual re-verification of prior rejection, no competing options
- Prior review + research both confirmed at 0.95 confidence

### Action
This task has completed a full reject → research → backlog cycle. Research confirmed the premise is invalid (T1 — no action required). **Recommend closing/archiving this task.** No code changes are needed. If adding timestamps to TaskSummary is desired, that is a feature change requiring a separate task with correct AC.
[[2026-04-14]]
## Research (validation pass)

Re-verified existing research doc `.owlbear/research/stale-tasksummary-excludes-841.md` against current codebase (2026-04-14). All prior findings confirmed:

- **Model docstring** (models.py:91–96): "Excludes body, claimed_by, created, and updated" — unchanged
- **Model fields**: TaskSummary does NOT declare `created`/`updated`; `extra="ignore"` drops them
- **Test file** `_EXCLUSION_FIELDS` (test_tasksummary_model_801.py:61–67): `{"body", "created", "updated", "claimed_by", "claimed_at", "file"}` — correct per model design
- **All 14 tests pass** (verified via pytest)
- **Implementing the AC would break correct tests** — `test_temporal_fields_not_in_construction_output` would fail (model_dump never contains created/updated)

**Verdict:** Premise invalid. No code changes needed. Task should be archived.

- Research doc: .owlbear/research/stale-tasksummary-excludes-841.md
- Sources: 5 studied, 4 high-relevance
- Finding: Premise invalid — no fix needed (confidence: 0.95)
- Follow-up tasks: none
- Decision requests: none
- Tier: T1 — no action required

## Challenge Results
- Challenger: SKIPPED — factual verification, no competing options
- Confidence in original: 0.95
[[2026-04-14]]
## Architecture Review (3rd cycle)

### Verdict: REJECT — premise invalid, confirmed by 2 prior reviews + 2 research cycles

### Re-verification (2026-04-14)
- **Model docstring** (models.py:91–96): "Excludes body, claimed_by, created, and updated" — unchanged
- **Model fields**: TaskSummary does NOT declare `created`/`updated`; `extra="ignore"` drops them
- **Test file** `_EXCLUSION_FIELDS` (test_tasksummary_model_801.py:61–67): `{"body", "created", "updated", "claimed_by", "claimed_at", "file"}` — correct per model design
- **All tests pass**: no stale tests exist
- **Dependency #851**: done/archived

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | AC contradicts the actual model. `created`/`updated` are intentionally excluded per model docstring and field declarations. Implementing AC would break currently-passing, correct tests. |

### Challenge Results
- Challenger: SKIPPED — factual re-verification of prior rejection (3rd cycle), no competing options
- Confidence: 0.95

### Action
**STRONGLY RECOMMEND ARCHIVING THIS TASK.** It has completed 3 reject→research→backlog cycles, each confirming the same conclusion: the premise is invalid and no code changes are needed. Re-researching will produce the same result. If adding timestamps to TaskSummary is desired, create a new feature task with correct AC.
[[2026-04-14]]
## Research (4th cycle — final validation pass)

Re-verified `.owlbear/research/stale-tasksummary-excludes-841.md` against codebase (2026-04-14). All findings confirmed unchanged:

- **Model docstring** (models.py:91–96): "Excludes body, claimed_by, created, and updated" — unchanged
- **Model fields**: TaskSummary does NOT declare `created`/`updated`; `extra="ignore"` drops them
- **Test file** `_EXCLUSION_FIELDS` (test_tasksummary_model_801.py:61–67): `{"body", "created", "updated", "claimed_by", "claimed_at", "file"}` — correct per model design
- **All 14 tests pass** (verified via pytest — 14 passed in 12.90s)
- **Implementing the AC would break correct tests** — `test_temporal_fields_not_in_construction_output` asserts created/updated are absent, which is correct

**Verdict: Premise invalid. No code changes needed. STRONGLY RECOMMEND ARCHIVING — this is the 4th cycle confirming the same conclusion.**

- Research doc: .owlbear/research/stale-tasksummary-excludes-841.md
- Sources: 5 studied, 4 high-relevance
- Finding: Premise invalid — no fix needed (confidence: 0.95)
- Follow-up tasks created: none (no action required)
- Decision requests: none
- Tier: T1 — no action required

## Challenge Results
- Challenger: SKIPPED — factual verification, no competing options
- Confidence in original: 0.95
[[2026-04-14]]
## Architecture Review (4th cycle — BLOCK to break loop)

### Verdict: BLOCK — premise invalid, infinite reject/research loop detected

### Re-verification (2026-04-14)
- **Model docstring** (models.py:91–96): "Excludes body, claimed_by, created, and updated" — created/updated are INTENTIONALLY EXCLUDED
- **Model fields**: TaskSummary does NOT declare `created` or `updated`; `extra="ignore"` drops them silently
- **Test file** `_EXCLUSION_FIELDS` (test_tasksummary_model_801.py:60–67): `{"body", "created", "updated", "claimed_by", "claimed_at", "file"}` — CORRECT per model design
- **All 14 tests pass**: no stale tests exist
- **Dependency #851**: done/archived

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| `_EXCLUSION_FIELDS` removes `created`/`updated` | INVALID | Model docstring explicitly lists these as excluded. Removing them would break tests. |
| Exclusion set is `{body, claimed_by, claimed_at, file}` only | INVALID | Correct set includes `created` and `updated` (6 fields, not 4) |
| `test_temporal_fields_not_in_construction_output` rewritten to assert presence | INVALID | This test is correct — `model_dump()` never contains created/updated because the model excludes them |
| Module-level docstring AC2 comment corrected | INVALID | AC2 comment already matches the correct exclusion set |
| All `TestFromAC_TaskSummaryExcludes` tests pass | ALREADY TRUE | All 14 tests pass right now |
| No other tests regress | N/A | No changes needed |

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Premise challenge | FAIL | Every AC line is based on a misquote of the model docstring. The task claims TaskSummary "intentionally includes timestamps" — the opposite is true. |

### Loop Analysis
This task has completed 3 full reject-research-backlog cycles (reviews on 2026-04-13, 2026-04-13, 2026-04-14; research on 2026-04-13, 2026-04-14). Each cycle confirmed identical findings at 0.95 confidence. Rejecting to research again will produce the same result.

### Challenge Results
- Challenger: SKIPPED — 4th cycle of factual re-verification, no competing interpretations remain
- Confidence: 0.95

### Recommendation
**ARCHIVE THIS TASK.** No code changes are needed. The tests are correct. If adding timestamps to TaskSummary is desired in the future, that is a feature change requiring a new task with correct AC.
