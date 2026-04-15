# Task #841 — Fix stale TestFromAC_TaskSummaryExcludes tests

> **Owning task:** #841 — Fix stale TestFromAC_TaskSummaryExcludes tests (created/updated in exclusion set)
> **Date:** 2026-04-13  **Status:** Complete — premise invalid

## 1. Context and Question

Task #841 asserts that `_EXCLUSION_FIELDS` in `test_tasksummary_model_801.py` incorrectly lists `created` and `updated`, claiming the TaskSummary model "includes timestamps per model docstring." The task asks to remove those two fields from the exclusion set and rewrite `test_temporal_fields_not_in_construction_output` to assert they ARE present. This research verifies whether the premise is correct.

## 2. Sources Studied

| # | Source | Relevance |
|---|--------|-----------|
| 1 | `serve/kanban/src/owlbear_kanban/models.py:99-122` — TaskSummary class with docstring | 1.0 |
| 2 | `tests/test_tasksummary_model_801.py:51-57,149-176` — `_EXCLUSION_FIELDS` + `TestFromAC_TaskSummaryExcludes` | 1.0 |
| 3 | `.owlbear/research/task-845-tasksummary-test-redundancy.md` §3c — confirming exclusion design | 0.9 |
| 4 | Task #851 (done) — sibling fix for `TestFromAC_ListTasks` migration tests | 0.8 |
| 5 | Architecture review in task #841 body — prior agent analysis | 1.0 |

## 3. Analysis

### 3a. Premise check — what does the model actually exclude?

| Claim (task AC) | Actual (source 1) | Match? |
|-----------------|-------------------|--------|
| Docstring says "excludes body and claimed_by" | Docstring says "Excludes body, claimed_by, created, and updated" | NO |
| TaskSummary includes `created`/`updated` fields | TaskSummary does NOT declare `created`/`updated`; `extra="ignore"` drops them | NO |

### 3b. Test correctness

| Test | Assertion | Correct? |
|------|-----------|----------|
| `test_excluded_fields_absent_from_schema` | `_EXCLUSION_FIELDS ∩ model_fields == ∅` | YES — all 6 fields are absent |
| `test_temporal_fields_not_in_construction_output` | `{created, updated} ∩ model_dump().keys() == ∅` | YES — model drops them |
| All 14 tests in file | PASS (verified via `pytest -v`) | YES |

### 3c. Impact of implementing the AC

Removing `created` and `updated` from `_EXCLUSION_FIELDS` would cause `test_excluded_fields_absent_from_schema` to pass vacuously for those fields (correct but weaker). Rewriting `test_temporal_fields_not_in_construction_output` to assert presence would FAIL immediately — `model_dump()` never contains `created` or `updated`.

**Implementing the AC would break currently-passing, correct tests.**

## 4. Recommendation

**Close task #841 — no fix needed.** The tests are correct as-is. The task's root cause analysis misquoted the model docstring. Confidence: **0.95**.

Tier: T1 — no action required (invalid premise, no code changes).

Challenge: SKIPPED — no competing options exist; finding is factual verification, not a design choice.

## 5. Follow-up Tasks

None. No code changes are needed. The sibling task #851 (stale ListTasks tests) is already done.
