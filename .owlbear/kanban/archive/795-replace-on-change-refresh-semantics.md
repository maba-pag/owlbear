---
id: 795
title: Replace-on-change refresh semantics
status: archived
priority: medium
created: '2026-04-10T12:31:51.917663+00:00'
updated: '2026-04-13T12:43:51.024905+00:00'
tags:
- phase-1
- scope:knowledge
parent: 775
depends_on:
- 791
blocked: false
block_reason: null
claimed_by: null
claimed_at: null
---
## Acceptance Criteria

- `ingest.py` changed branch calls `delete_document_data(conn, existing_id)` before inserting the new document
- Ghost document bug (F1) fixed — `existing_id` now used in the content-changed path
- All #791 tests pass; existing ingest tests still pass
- File: `serve/knowledge/src/owlbear_knowledge/ingest.py`

## Context
- WS-D: Pipeline Integration
- Scope item 10 from #775
- See research F1: ghost document bug — delete_document_data() already exists for cascade

[[2026-04-12]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One fix: delete-before-insert in content-changed branch |
| Interface clarity | PASS (minor nit) | AC1 says `delete_document_data(conn, existing_id)` but actual API is `self._docs.delete_document_data(document_id)` — no `conn` param. Cosmetic; implementation already correct |
| Dependency correctness | PASS | #791 (test task) is `done`; #785 (schema v9, transitive dep) is `done` |
| Module layering | PASS | IngestPipeline → DocumentStore — correct direction |
| TDD compliance | PASS | Test task #791 completed with 10 tests in `test_replace_on_change_775.py` |
| KISS/YAGNI | PASS | Minimal scope — one bug fix |
| Premise challenge | NOTE | Implementation already exists at `ingest.py:190-196`. See below |
| Pattern consistency | PASS | Follows existing `self._docs.method()` pattern |
| Security surface | PASS | No new system boundary |
| Single domain | PASS | Knowledge domain only |

### Implementation Already Complete

The fix described by all AC lines is already present in the codebase:

- `ingest.py` L190-196: `if existing_id is not None: self._docs.delete_document_data(existing_id)` precedes `self._docs.insert_document(doc_id, intake, scope=scope)`
- `test_replace_on_change_775.py`: 10 tests cover delete-before-insert, ghost doc regression, and unchanged-content skip
- All tests reportedly passing

**Builder guidance:** Verify the implementation is in place, run tests, and advance. No new code expected.

### AC Signature Nit

AC1 references `delete_document_data(conn, existing_id)`. The actual DocumentStore method signature is `delete_document_data(self, document_id: str)` — the `conn` is managed internally by DocumentStore. This is cosmetically inaccurate but the implementation is correct.

### Challenge Results

- Challenger: **reconsider** (confidence 0.85) — implementation already complete, advancing to `todo` is procedurally wasteful
- Architect response: **acknowledged but overridden** — pipeline protocol requires routing through `todo` so the test-writer can process the task. Downstream agents will verify and fast-track via pass-through notes. Noted implementation-complete status in builder guidance above.

### Verdict: APPROVE
### Action Taken: Advanced to `todo`. Implementation already in place — downstream agents should verify and fast-track.
[[2026-04-12]]
## Test-Writer Notes

**Pass-through: implementation already complete — no new tests written.**

### Evidence

- Architecture review explicitly flagged: "Implementation already exists at `ingest.py:190-196`" and directed downstream agents to "fast-track via pass-through notes."
- Dependency task #791 (test task) delivered `test_replace_on_change_775.py` with 10 tests covering all AC lines.
- Verified 10/10 tests PASS against current codebase.

### AC Coverage (by existing tests in `tests/test_replace_on_change_775.py`)

| AC | Coverage |
|----|----------|
| AC1: `delete_document_data(existing_id)` called before insert | `test_delete_called_with_exact_existing_id`, `test_delete_precedes_insert_when_content_changes` |
| AC2: Ghost document bug fixed (F1 regression) | `test_f1_regression_ghost_doc_not_left_after_change`, `test_back_to_back_changes_each_delete_own_prior` |
| AC3: All #791 tests pass; existing ingest tests still pass | Verified — 10/10 pass |
| AC4: File `serve/knowledge/src/owlbear_knowledge/ingest.py` | Implementation confirmed at L190-196 |

**No new tests created.** Builder only needs to verify and advance.
[[2026-04-12]]
## Builder Notes

**Pass-through: implementation already in place — no new code written.**

### Evidence (verified by builder)
- `serve/knowledge/src/owlbear_knowledge/ingest.py` L190-196: `if existing_id is not None: self._docs.delete_document_data(existing_id)` already present before insert call.
- Tests: `tests/test_replace_on_change_775.py` — **10/10 PASSED**
- Ruff: **clean** on `ingest.py`

### AC Coverage
| AC | Status |
|----|--------|
| AC1: `delete_document_data(existing_id)` called before insert | PASS |
| AC2: Ghost document bug (F1) fixed | PASS |
| AC3: All #791 tests pass; existing ingest tests still pass | PASS |
| AC4: File `ingest.py` | CONFIRMED |

No files changed. No commits needed.
[[2026-04-13]]
## Review Evidence

### Test Results
pytest: **22 passed, 0 failed** (scoped to `test_replace_on_change_775.py` + `test_cleaned_content_hash_replace_on_change_764.py`)

### Lint
ruff: **clean** — `serve/knowledge/src/owlbear_knowledge/ingest.py` + test file

### Coverage
`owlbear_knowledge.ingest`: 64% — below 90% threshold, but **suppressed per Step 6 suppressions** ("coverage gaps in untouched code"). Builder made zero code changes; the gap is entirely in pre-existing paths unrelated to this AC.

---

### Pass 1 Critical Checks

**5.0 TestFromAC Audit**
`TestFromAC_ReplaceOnChangeSemantics` — 10 tests, none modified by builder (no files changed).

| AC Line | Mapped Test(s) | Would Fail if AC Violated? | Verdict |
|---------|---------------|---------------------------|---------|
| AC1: delete before insert | `test_delete_called_with_exact_existing_id`, `test_delete_precedes_insert_when_content_changes` | Yes — `assert_called_once_with(prior_id)` + index ordering assertion | COVERED |
| AC2: ghost doc regression | `test_f1_regression_ghost_doc_not_left_after_change`, `test_back_to_back_changes_each_delete_own_prior` | Yes — strict call-with-ID + call_count==2 + exact args | COVERED |
| AC3: unchanged skips | `test_unchanged_content_skips_delete`, `test_unchanged_content_skips_insert` | Yes — `assert_not_called()` | COVERED |

**5.1 Security** — No new code. `delete_document_data` receives a UUID from internal store — no user-controlled input on this path. PASS.

**5.2 TestFromAC Comparison** — No files changed; no TestFromAC modifications. PASS.

**5.3 Test Quality** — STRONG. All assertions specify exact arguments (`assert_called_once_with(prior_id)`), order verification via `call_order.index()`, `assert_not_called()` on skip paths, `call_count == 2` with positional arg verification. Names descriptive. No shared mutable state.

**5.4 Data Safety** — No new data paths introduced. PASS.

**5.5 Test Gap Analysis** — Changed path at ingest.py L196-199 fully exercised: delete-with-correct-id ✓, delete-before-insert order ✓, no-prior-id skip ✓, back-to-back ✓. PASS.

**5.7 Builder Process Quality** — CLEAN. Single pass-through note, consistent with architect + test-writer guidance.

---

### AC Compliance

| AC | Evidence | Mapped Test | Status |
|----|----------|-------------|--------|
| AC1: changed branch calls `delete_document_data(existing_id)` before insert | ingest.py L196: `if existing_id is not None: self._docs.delete_document_data(existing_id)` precedes L199: `self._docs.insert_document(...)` | `test_delete_precedes_insert_when_content_changes` | PASS |
| AC2: ghost document bug fixed — `existing_id` used | Same L196 confirms prior-ID deletion; F1 regression test verifies no ghost remains | `test_f1_regression_ghost_doc_not_left_after_change` | PASS |
| AC3: all #791 tests pass; existing ingest tests pass | 22/22 PASS, ruff clean | full run | PASS |
| AC4: file `ingest.py` | `serve/knowledge/src/owlbear_knowledge/ingest.py` confirmed | n/a | PASS |

*Informational: AC1 text says `delete_document_data(conn, existing_id)`; actual signature is `delete_document_data(document_id: str)` — cosmetic AC nit, already noted by architect, implementation correct.*

---

### Deductions
- 0 critical deductions
- Informational: pre-existing 64% ingest.py coverage gap (suppressed)

**Confidence: .95 → PASS**
[[2026-04-13]]
## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` has no knowledge/ingest entries; replace-on-change is an internal pipeline behavior with no agent-facing convention to update |
| 2 | Module docstrings | Yes | Updated | `ingest()` docstring was missing the replace-on-change semantics (delete-before-insert when content changes). Added "Replace-on-change semantics" paragraph documenting `delete_document_data(existing_id)` cascade and ghost-doc prevention. Commit: `5979e1bc` |
| 3 | External attribution | No | N/A | Fix uses pre-existing `delete_document_data()` — no external patterns, no new attribution needed |
| 4 | CLI changes | No | N/A | `ingest.py` is an internal pipeline module; no CLI surface affected |
| 5 | Research doc | Yes | Verified | `.owlbear/research/775-phase1-browser-pipeline-schema.md` exists; F1 entry (line 62) documents ghost doc bug and fix strategy. Task body references it. |

### Files Updated
- `serve/knowledge/src/owlbear_knowledge/ingest.py` — docstring only (commit `5979e1bc`)

### Scratch Files
- No `.owlbear/scratch/795-*` files found — nothing to clean.
[[2026-04-13]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: changed branch calls `delete_document_data(existing_id)` before insert | `ingest.py` L206-207: `self._docs.delete_document_data(existing_id)` precedes L209: `self._docs.insert_document(...)` | PASS |
| AC2: Ghost doc bug fixed — `existing_id` used in content-changed path | Same L206: `existing_id` flows from `check_content_changed` return; `test_f1_regression_ghost_doc_not_left_after_change` covers regression | PASS |
| AC3: All #791 tests pass; existing ingest tests pass | 22/22 scoped tests pass (`test_replace_on_change_775.py` 10/10, `test_cleaned_content_hash_replace_on_change_764.py` 12/12) | PASS |
| AC4: File `ingest.py` | `serve/knowledge/src/owlbear_knowledge/ingest.py` exists, implementation at L206-209 | PASS |

### Test Results
- pytest (full suite): 4,083 passed, 352 failed, 8 skipped — **0 failures in task scope**. 352 failures are pre-existing across unrelated modules (entity extraction, mcp-browser, kanban engine, etc.)
- pytest (scoped): 22/22 PASS
- ruff: clean (0 violations)

### Reviewer Evidence
Present, detailed, PASS at .95. Thorough TestFromAC audit, security check, test quality assessment, coverage suppression justified. Trusted.

### Architect Quality: 4/5
AC lines specific enough to verify. Minor cosmetic nit: AC1 says `delete_document_data(conn, existing_id)` but actual signature is `delete_document_data(document_id)` — noted by architect, implementation correct. Edge cases covered by tests (back-to-back changes, unchanged skip, F1 regression). Architect correctly noted implementation was already complete and provided builder guidance.

### Deduction Breakdown
- AC lines without evidence: 0 × -.02 = 0
- Lint violations: 0 × -.05 = 0
- AC quality ≤ 3: N/A (4/5)
- Missing reviewer evidence: N/A (present)
- Full-suite failures in task scope: 0 × -.05 = 0
- Total deductions: 0

### Confidence: 1.00
### Action: archive

### Commit Integrity
- Docs commit `5979e1bc` verified for `ingest.py` docstring update
- Implementation pre-existing (no code changes by builder) — no new code commits expected
- No uncommitted task deliverables