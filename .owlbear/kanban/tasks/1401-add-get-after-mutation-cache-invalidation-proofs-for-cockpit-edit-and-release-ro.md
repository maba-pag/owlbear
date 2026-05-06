---
id: 1401
title: Add GET-after-mutation cache invalidation proofs for cockpit edit and 
  release routes
status: in-progress
priority: nice-to-have
created: 2026-05-06T03:40:00.756804+00:00
updated: 2026-05-06T05:06:39.001804+00:00
tags:
- cockpit
- cache
- test
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Follow-up from #1346 reviewer recommendation #2. Currently only the move-route has a GET `/api/tasks` assertion proving cache invalidation after `POST /api/tasks/{id}/move` (at `tests/test_cockpit_cache_sse_1346.py:565`). Edit and release routes lack matching proofs.

## Acceptance Criteria

1. A test proves that `GET /api/tasks` reflects title changes after a successful `POST /api/tasks/{id}/edit` with a title mutation. The test must locate the mutated task by ID in the response list and assert its `title` field equals the new value, not the pre-edit value. (td:1)
2. A test proves that `GET /api/tasks` reflects tag changes after a successful `POST /api/tasks/{id}/edit` with a tags mutation. The test must assert that the mutated task's `tags` field exactly matches the replacement tag list (not merely that new tags are present — removed tags must be absent). (td:1)
3. A test proves that `GET /api/tasks` reflects claimed-state changes after a successful `POST /api/tasks/{id}/release`. The test must locate the released task by ID and assert `claimed` is `false`. (td:1)
4. All new tests follow the prime→mutate→re-read pattern: prime cache via initial `GET /api/tasks`, perform mutation via the corresponding `POST` route, then assert a fresh `GET /api/tasks` reflects the change. The assertion strategy is field-inspection on the task summary object (differs from the move-route proof which uses filter-exclusion). (td:0)
5. Existing tests remain green; no weakening of existing assertions. (td:0)

## Key Files

- `tests/test_cockpit_cache_sse_1346.py` — existing move-route proof pattern (prime→mutate→re-read)
- `tests/test_cockpit_mutation_api.py` — existing edit/release route tests (POST-only, no GET proof)
- `serve/cockpit/src/owlbear_cockpit/routes/read.py` — cache invalidation logic under proof
- `serve/cockpit/src/owlbear_cockpit/cache.py` — `MtimeScanCache` (passive invalidation via mtime)

## Scope

- **In scope:** Test-only additions proving GET-after-mutation cache invalidation for edit (title, tags) and release (claimed state).
- **Out of scope:** Implementation changes to cache.py, read.py, or mutation routes. Cache populate ordering hardening (separate concern tracked in #1346 follow-up recommendation #1). Proofs for `block_reason`/`blocked` summary changes (can follow separately if needed).

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: cache invalidation proofs for edit/release routes |
| Interface clarity | PASS | AC specifies exact mutations, assertion targets, and field-inspection strategy |
| Dependency correctness | PASS | No dependencies; existing pattern and fixtures available |
| Module layering | PASS | Test-only; no production code changes |
| TDD compliance | PASS | Task IS a test task (tagged `test`) |
| KISS/YAGNI | PASS | Three focused test functions, minimal scope |
| Premise challenge | PASS | Reviewer #1346 identified this gap; move-route has proof, edit/release don't |
| Pattern consistency | PASS | Follows established prime→mutate→re-read pattern from test_cockpit_cache_sse_1346.py |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Cockpit domain only |

### Challenge Results
- Challenger: reconsider (0.66)
- Issues raised: (1) assertion-shape mismatch between move-route filter-exclusion and title/release field-inspection, (2) AC2 tag false-green risk, (3) incomplete closure of #1346 rec #2
- Architect response: accepted (1) and (2) — refined AC to specify field-inspection strategy and exact tag-list replacement assertion. Rebutted (3) — scope narrowing is intentional; block_reason/blocked proofs can follow separately.

### Test Depth
- Max depth: 1
- Test-writer: PROCEED (but task tagged `test` — pass-through expected)

### Verdict: APPROVE
### Action Taken: Refined AC to clarify field-inspection assertion strategy (vs filter-exclusion), require exact tag-list replacement assertion, and acknowledge scope narrowing. Approved to todo.
[[2026-05-06]]
## Architecture Review

Refined AC based on challenger feedback (0.66 confidence, reconsider):
- AC1/AC3: Clarified field-inspection assertion strategy (locate task by ID, assert field value) — distinct from move-route's filter-exclusion pattern
- AC2: Strengthened to require exact tag-list replacement assertion (removed tags must be absent, not just new tags present)
- AC4: Clarified prime→mutate→re-read is the shared pattern; assertion strategy varies by mutation type
- Scope: Acknowledged intentional narrowing (no block_reason/blocked proofs)

All 10 evaluation criteria PASS. Test-only task, no production code changes. Tagged `test` for test-writer pass-through.
[[2026-05-06]]
## Test-Writer Notes

**Test file:** `tests/test_cockpit_cache_sse_1401.py`
**Class:** `TestFromAC_EditReleaseCacheInvalidation`

### Tests per category
| Category | Count | Tests |
|----------|-------|-------|
| Happy / Proof | 3 | All three AC items |
| Edge / Error / Boundary | 0 | AC scope is proof-only (td:1 × 3) |

**Total:** 3 tests — all PASS (implementation already correct from #1346)

### AC coverage
| AC | Test | Status |
|----|------|--------|
| AC1 — title reflected after edit | `test_get_tasks_reflects_title_after_edit_route` | ✅ PASS |
| AC2 — exact tag replacement reflected after edit | `test_get_tasks_reflects_tags_after_edit_route` | ✅ PASS |
| AC3 — claimed=False reflected after release | `test_get_tasks_reflects_claimed_false_after_release_route` | ✅ PASS |
| AC4 — prime→mutate→re-read pattern used | all three tests | ✅ structural |
| AC5 — existing tests remain green | ruff+pytest scoped pass | ✅ |

### Advance rationale
All new tests PASS against current code — cache invalidation for edit and release routes was implemented as part of #1346. No builder work required. Advancing directly to review per w-tdd-red §1b.1 logic (implementation already handles the proof cases).

### Quality
- Ruff: 0 errors (exit 0)
- Pattern: prime→mutate→re-read with field-inspection (distinct from move-route filter-exclusion)
- Preconditions explicitly asserted before each mutation
[[2026-05-06]]
Direct-to-review advance: all 3 proof tests pass against current code. Implementation (MtimeScanCache + cockpit edit/release routes) already correct from #1346. No builder work required.
[[2026-05-06]]
## Review Evidence
### Test Results
- pytest: 56 passed, 0 failed
- Scoped task file: tests/test_cockpit_cache_sse_1401.py = 3 passed
- Adjacent regression: tests/test_cockpit_mutation_api.py = 53 passed
- Reflog evidence confirms a task-scoped test-writer commit: 0a8beeaa test: add GET-after-mutation cache proofs for edit and release routes (#1401, test-writer)

### Lint: clean
- Ruff on tests/test_cockpit_cache_sse_1401.py: 0 errors

### Coverage: informational for this test-only task
- serve/cockpit/src/owlbear_cockpit/cache.py: 79%
- serve/cockpit/src/owlbear_cockpit/routes/read.py: 73%
- serve/cockpit/src/owlbear_cockpit/routes/mutation.py: 57%

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: GET /api/tasks reflects title changes after successful edit | test_get_tasks_reflects_title_after_edit_route | Yes. Exact title equality is asserted at tests/test_cockpit_cache_sse_1401.py:150 after the prime / mutate / re-read sequence at :126, :136, :146. | COVERED |
| AC2: GET /api/tasks reflects exact tag replacement after successful edit | test_get_tasks_reflects_tags_after_edit_route | No. The task header narrows the proof to new tags present and removed tags absent at tests/test_cockpit_cache_sse_1401.py:7, and the body only asserts membership and non-membership at :217, :219, :222, :226. It never asserts exact equality, so stale keep-tag or any other extra tag would still pass. | LAX |
| AC3: GET /api/tasks reflects claimed=false after successful release | test_get_tasks_reflects_claimed_false_after_release_route | Yes. Exact boolean equality is asserted at tests/test_cockpit_cache_sse_1401.py:293 after the prime / mutate / re-read sequence at :269, :279, :289. | COVERED |
| AC4: New tests use the prime / mutate / re-read pattern with field inspection | all three tests | Yes. Each test does initial GET, mutation POST, then fresh GET at tests/test_cockpit_cache_sse_1401.py:126, :136, :146; :193, :203, :213; :269, :279, :289. | COVERED |
| AC5: Existing tests remain green; no weakening of existing assertions | quality-runner scoped plus adjacent regression run | Yes for the evidence gathered here: 56 passed, 0 failed, ruff clean. | COVERED |

#### Security Review
- No issues. Test-only task with no new runtime boundary or dependency.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing TestFromAC suites in related cockpit files | No weakening evidenced in task notes or reflog. This task appears to add a new test file rather than modify existing TestFromAC assertions. Exact HEAD vs working-tree diff could not be proven in this tool surface. | PRESERVED (small confidence deduction) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC2 requires exact replacement, but tests/test_cockpit_cache_sse_1401.py:217-226 only checks presence of the two new tags and absence of old-tag. It does not fail on extra stale tags. |
| Negative/error-path coverage | ADEQUATE | td:1 proof task; ACs are happy-path proof checks only. |
| Manual mutation reasoning | WEAK | If GET /api/tasks returned [new-tag, another-tag, keep-tag], AC2 would be violated but the current test would still pass. |
| Test independence | STRONG | Each test creates its own temp board and clears dependency overrides. |
| Descriptive test names | STRONG | Test names map directly to the stated AC behaviors. |

#### Data Safety
- No issues. Temp-board tests only.

#### Implementation-Aware Gaps
- No production-path gap found for AC1 or AC3. The blocking issue is proof quality in AC2, not implementation evidence.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 0 |
| Approach variation | N/A |
| Assessment | CLEAN (builder skipped; test-writer advanced directly to review) |

### Pass 2 - INFORMATIONAL
- No prior Review Evidence section exists in the live task file, so this is the first review cycle.
- Existing POST-only tag test already uses an exact-set pattern at tests/test_cockpit_mutation_api.py:270-280; the new GET-after-mutation proof should be at least that discriminating.
- Dirty-tree contamination could not be conclusively checked because terminal git status/diff was unavailable in this tool surface. Small confidence deduction applied.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Exact title equality at tests/test_cockpit_cache_sse_1401.py:150 | test_get_tasks_reflects_title_after_edit_route | PASS |
| AC2 | Membership-only tag checks at tests/test_cockpit_cache_sse_1401.py:217-226 do not prove exact replacement | test_get_tasks_reflects_tags_after_edit_route | FAIL |
| AC3 | Exact claimed=false assertion at tests/test_cockpit_cache_sse_1401.py:293 | test_get_tasks_reflects_claimed_false_after_release_route | PASS |
| AC4 | Prime / mutate / re-read pattern appears in all three tests at tests/test_cockpit_cache_sse_1401.py:126, :136, :146; :193, :203, :213; :269, :279, :289 | all three tests | PASS |
| AC5 | quality-runner evidence: 56 passed, 0 failed; lint clean | scoped task suite plus adjacent mutation_api regression | PASS |

### Confidence: 0.84
### Verdict: FAIL
### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | test-writer | Strengthen the AC2 GET-after-edit tags proof to assert exact replacement equality for the task summary tags field, not membership-only checks; make the assertion fail if any stale or extra tag remains. | tests/test_cockpit_cache_sse_1401.py | Test Quality finding at tests/test_cockpit_cache_sse_1401.py:7 and :217-226; stronger exact-set pattern already exists at tests/test_cockpit_mutation_api.py:270-280 |
[[2026-05-06]]
## Test-Writer Notes
- Retry: strengthened AC2 tag assertion to exact set equality per reviewer Required Follow-up #1.
- Change: replaced 3 membership-only checks (`in` / `not in`) with single `assert actual_tags == {"new-tag", "another-tag"}` — any stale or extra tag now fails the test.
- All 3 tests PASS against current code (implementation already applies full-replacement semantics).
- Builder skip: test-only retry, all tests green.
- Ruff: clean (0 errors).
- Commit: 1e9fb275 test: strengthen AC2 tag exact-set assertion for cache invalidation proof (#1401, test-writer)