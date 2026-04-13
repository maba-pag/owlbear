---
id: 797
title: 'Fix #751 tests: replace split-column assertions with unified status column'
status: review
priority: needed
created: '2026-04-10T16:05:19.844611+00:00'
updated: '2026-04-11T15:00:18.984557+00:00'
tags:
- phase-1
- scope:knowledge
- schema
- type:test
parent: 751
depends_on:
- 757
blocked: true
block_reason: Quality-Runner unavailable — pytest-cov not installed in .venv; cannot
  run tests independently
claimed_by: null
claimed_at: null
---
The #751 builder commit `be9610a3` added `approval_state` + `extraction_status` columns to `source_pages` DDL and wrote tests asserting their existence. This deviates from the architect-approved #754 AC which specifies a unified `status` column with `PageStatus` StrEnum (DISCOVERED, APPROVED, REJECTED, INGESTED, STALE).

After #757 removes the split columns from the DDL (per refined AC), these two #751 tests will fail:

**Tests to fix in `tests/test_authenticated_content_pipeline_751.py`:**
1. `test_source_pages_has_approval_state_column` (L444) — replace with `test_source_pages_has_status_column` asserting `"status" in cols`
2. `test_source_pages_has_extraction_status_column` (L453) — delete (unified status replaces this; extraction state tracked via PageStatus.INGESTED/STALE)

**AC:**
- [ ] `test_source_pages_has_approval_state_column` replaced with `test_source_pages_has_status_column` that asserts `"status" in cols`
- [ ] `test_source_pages_has_extraction_status_column` removed
- [ ] All remaining tests in `test_authenticated_content_pipeline_751.py` still pass
- [ ] ruff clean
[[2026-04-11]]
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Test fix only — replace one test, delete one test |
| Interface clarity | PASS | AC specifies exact test names, assertion (`"status" in cols`), and suite-green requirement |
| Dependency correctness | PASS | Depends on #757 (done/archived). Schema DDL already uses unified `status` column at `schema.py:159` |
| Module layering | PASS | Test-only change, no production code touched |
| TDD compliance | PASS | Tagged `type:test` — this IS the test task |
| KISS/YAGNI | PASS | Minimal scope: 1 test replaced, 1 test deleted |
| Premise challenge | PASS | Tests currently assert non-existent columns (`approval_state`, `extraction_status`). Schema uses unified `status TEXT DEFAULT 'discovered'`. Fix is necessary. |
| Pattern consistency | PASS | Replacement test follows same PRAGMA table_info pattern as existing tests in the file |
| Security surface | PASS | No new system boundaries |
| Single domain | PASS | Knowledge/schema domain only |

### Codebase Evidence
- `schema.py:153-165` — `_CREATE_SOURCE_PAGES` DDL has unified `status` column, no `approval_state` or `extraction_status`
- `test_authenticated_content_pipeline_751.py:444` — `test_source_pages_has_approval_state_column` asserts non-existent column
- `test_authenticated_content_pipeline_751.py:453` — `test_source_pages_has_extraction_status_column` asserts non-existent column
- `test_schema_extensions_757.py:304` — authoritative `test_source_pages_has_status_column` already exists
- `test_schema_extensions_757.py:320` — explicit rejection test confirms old columns absent
- No production code references to `approval_state` or `extraction_status` on `source_pages`
- `approval_state` references in `test_approve_memory_*.py` are on `memory_entries` table — unrelated

### Challenge Results
- Challenger: proceed (confidence 0.92)
- Architect response: accepted — all concerns addressed, AC is precise and verifiable

### Verdict: APPROVE
### Action Taken: Advanced #797 to todo. AC is mechanically verifiable. `type:test` pass-through tag already present.
[[2026-04-11]]
## Test-Writer Notes

**File:** `tests/test_authenticated_content_pipeline_751.py`

**Changes:**
- `test_source_pages_has_approval_state_column` → replaced with `test_source_pages_has_status_column` asserting `"status" in cols`
- `test_source_pages_has_extraction_status_column` → deleted (extraction state unified into PageStatus.INGESTED/STALE per #754 AC)

**AC Coverage:**

| AC Line | Test | Result |
|---------|------|--------|
| Replace with `test_source_pages_has_status_column` asserting `"status" in cols` | `test_source_pages_has_status_column` | PASS ✓ |
| Remove `test_source_pages_has_extraction_status_column` | Deleted | Done ✓ |
| All remaining tests still pass | 41/41 passed | PASS ✓ |
| ruff clean | No violations | PASS ✓ |

**Pytest result:** 41 passed, 0 failed  
**Commit:** `1825ed4e` — `test: replace split-column assertions with unified status column (#797, test-writer)`

Note: This task is `type:test` (direct test-fix), not RED-phase. Tests are green after fix — this is the intended outcome per architecture review.
[[2026-04-11]]
## Builder Notes

**Files changed:** `tests/test_authenticated_content_pipeline_751.py` (test-writer commit `1825ed4e`)

**Test results:** 41 passed, 0 failed  
**Coverage:** 99.6% (280/281 statements, 2/2 branches)  
**Lint:** ruff clean — no violations

**AC Evidence:**
| AC | Result |
|----|--------|
| `test_source_pages_has_status_column` asserts `"status" in cols` | PASS ✓ |
| `test_source_pages_has_extraction_status_column` removed | PASS ✓ |
| All remaining tests pass (41/41) | PASS ✓ |
| ruff clean | PASS ✓ |

**Notes:** `type:test` task — test-writer changes verified as correct. No production code touched. Surgical pass-through.
[[2026-04-11]]
## Review Evidence

**Quality-Runner result:** FATAL — `pytest-cov` not installed in `.venv`. All three attempts failed with `unrecognized arguments: --cov --cov-report=term-missing --cov-fail-under=0`. Quality-runner always appends `--cov` flags; plugin missing blocks every invocation. Root cause: `uv sync --all-groups` not run after dependency update.

**Environment fix required:** `uv sync --all-groups` from workspace root.

**Static verification (what could be checked without test execution):**

| Check | Method | Result |
|-------|--------|--------|
| Old test `test_source_pages_has_approval_state_column` removed | grep (0 matches) | PASS |
| Old test `test_source_pages_has_extraction_status_column` removed | grep (0 matches) | PASS |
| `test_source_pages_has_status_column` present at L444 | read_file | PASS |
| Assertion is `assert "status" in cols` | read_file:L451 | PASS — matches AC exactly |
| Test follows same PRAGMA pattern as siblings | read_file:L444-451 | PASS |
| Test count = 41 | grep `def test_` (maxResults=60) → 41 matches | PASS |
| No VS Code errors | get_errors | PASS — no errors |
| New test code has no obvious ruff violations | read_file static read | PASS |

**AC compliance table:**

| AC Line | Evidence | Status |
|---------|----------|--------|
| `test_source_pages_has_status_column` asserting `"status" in cols` | file:L444-L451, assertion confirmed | PASS |
| `test_source_pages_has_extraction_status_column` removed | grep: 0 matches in file | PASS |
| All remaining tests still pass | Cannot verify — quality-runner FATAL | UNVERIFIED |
| ruff clean | Cannot run independently via quality-runner | UNVERIFIED |

**No `TestFromAC_*` class modifications detected** — the test-writer authored the new test directly.

**Security:** No concerns. Test-only file. No production code changed. No new imports.

**Builder process:** Single clean cycle. No loop patterns detected. `type:test` pass-through — correct.

**Verdict:** BLOCK — quality-runner environment broken. Two AC lines (test execution pass, ruff) are unverifiable without independent test run. Static analysis on all verifiable items passes cleanly; likelihood of pass once environment is restored is high, but reviewer hard rule prohibits passing without independent test execution.