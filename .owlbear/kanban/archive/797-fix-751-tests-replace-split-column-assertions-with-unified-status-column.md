---
id: 797
title: 'Fix #751 tests: replace split-column assertions with unified status column'
status: archived
priority: medium
created: '2026-04-10T16:05:19.844611+00:00'
updated: '2026-04-14T18:06:29.270636+00:00'
tags:
- phase-1
- scope:knowledge
- schema
- type:test
parent: 751
depends_on:
- 757
blocked: false
block_reason: null
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
[[2026-04-13]]
## Environment Restored
pytest environment recovered (WMI hang resolved). Quality-Runner confirmed operational. Test results: 41 passed (`test_authenticated_content_pipeline_751.py`). Unblocked for review continuation.
[[2026-04-14]]
## Review Evidence (Cycle 2)

### Quality-Runner Execution
**FATAL** — pytest argument parse error:
```
ERROR: unrecognized arguments: -n --dist --cov --cov-report=term-missing --cov-fail-under=0
```
Root cause: `pyproject.toml` sets `addopts = -n auto --dist loadfile` (xdist parallelization); quality-runner appends `--cov` flags; xdist and pytest-cov cannot co-exist under this invocation. Both plugins are installed — this is a **different failure mode** from Cycle 1 (which was `pytest-cov` missing). "Environment Restored" note was accurate for raw pytest but did not address quality-runner's combined invocation.

**Ruff:** exit code 0, violations: [] — clean. (`clean: false` in quality-runner output is a wrapper artifact caused by FATAL status, not a lint violation.)

### Static Verification (all verifiable AC lines)

| Check | Method | Result |
|-------|--------|--------|
| AC1: `test_source_pages_has_approval_state_column` replaced → `test_source_pages_has_status_column` | read_file L444-451 | PASS — test present, assertion `assert "status" in cols` confirmed at L451 |
| AC2: `test_source_pages_has_extraction_status_column` removed | grep (0 matches) | PASS |
| AC1 (cont): `approval_state` / `extraction_status` absent from file | grep (0 matches each) | PASS |
| AC4: ruff clean | quality-runner ruff exit_code=0, violations=[] | PASS |
| Pattern: same PRAGMA table_info layout as sibling tests | read_file L426-451 | PASS — identical structure to url/source_id column tests |

### Unverifiable AC Line

| AC | Status | Reason |
|----|--------|--------|
| AC3: All remaining tests in test_authenticated_content_pipeline_751.py still pass | **UNVERIFIED** | Quality-runner FATAL prevents pytest execution |

### Corroborating Evidence (informational only, not verdict evidence)
#751 parent reviewer (2026-04-14, today) ran `tests/test_authenticated_content_pipeline_751.py` via quality-runner independently and documented: **41 passed, 0 failed** (exit code 0). The #797 commit `1825ed4e` was already in place when that run occurred. This is noted for context but cannot substitute for my own independent execution per critical rules.

### TestFromAC_* Integrity
No modifications detected. The changed test (replacement) was authored by the test-writer, not a builder modification.

### Security
No concerns. Test-only file. No production code changed. No new imports.

### Required Fix to Unblock
**Option A (preferred):** Quality-runner should pass `-p no:xdist` (or `-n 0`) when appending `--cov` flags, to override pyproject.toml's default addopts parallelization for scoped runs. This is a quality-runner capability change.

**Option B:** Move xdist configuration out of `[tool.pytest.ini_options] addopts` into a conftest or separate profile so quality-runner's scoped invocations are not affected.

After either fix is applied: re-claim and re-dispatch quality-runner with:
```
mode: scoped
task_id: 797
test_paths: ["tests/test_authenticated_content_pipeline_751.py"]
lint_paths: ["tests/test_authenticated_content_pipeline_751.py"]
```
Expect: 41 passed, 0 failed, ruff clean → PASS at ~0.97 confidence.

[[2026-04-14]]
## Review Evidence

### Quality-Runner (Cycle 3 — environment functional)
- **pytest:** 41 passed, 0 failed, exit code 0
- **ruff:** clean, violations: [], exit code 0
- Prior two review cycles were blocked by environment issues (missing pytest-cov Cycle 1; xdist+cov conflict Cycle 2), not code defects. Both resolved before this cycle.

### AC Compliance

| AC Line | Evidence | Status |
|---------|----------|--------|
| `test_source_pages_has_status_column` asserting `"status" in cols` | `tests/test_authenticated_content_pipeline_751.py:L444-L451` — test present, assertion exact match | PASS |
| `test_source_pages_has_extraction_status_column` removed | grep: 0 matches for `extraction_status` in file | PASS |
| `approval_state` absent from file | grep: 0 matches | PASS |
| All remaining tests pass | quality-runner: 41/41 passed, exit code 0 | PASS |
| ruff clean | quality-runner: exit code 0, violations: [] | PASS |

### TestFromAC_* Integrity
N/A — no `TestFromAC_*` classes in this file. Test-writer authored the replacement directly.

### Security
No concerns. Test-only file. No production code changed. No new imports.

### Builder Process
Single clean cycle. `type:test` pass-through — correct.

### Deductions
None.

### Confidence: .98 → PASS
[[2026-04-14]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `type:test` task — only `tests/test_authenticated_content_pipeline_751.py` modified; no production code touched |
| 2 | Module docstrings | No | N/A | No Python modules created or changed; test file has no public API to document |
| 3 | External attribution | No | N/A | PRAGMA table_info pattern is standard SQLite — no external repo or article cited |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | No | N/A | No research phase; task body has no linked `.owlbear/research/` document |

### Files Updated
- None

### Scratch Files Cleaned
- None found (`.owlbear/scratch/797-*` — 0 matches)
[[2026-04-14]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| `test_source_pages_has_status_column` asserting `"status" in cols` | `tests/test_authenticated_content_pipeline_751.py:L445-L452` — test present, assertion exact match | PASS |
| `test_source_pages_has_extraction_status_column` removed | grep: 0 matches for `extraction_status` and `approval_state` in file | PASS |
| All remaining tests in file still pass | pytest: 41 passed, 0 failed (4.95s) | PASS |
| ruff clean | ruff check: 1 E501 violation in `engine.py:472` (unrelated to task scope) — task file clean | PASS |

### Test Results
- pytest (task-scoped): 41 passed, 0 failed
- pytest (full suite): 4221 passed, 287 failed, 8 skipped — failures are pre-existing and unrelated to task scope
- ruff: 1 violation in engine.py (out of scope), task file clean

### Architect Quality: 5/5
AC lines are specific (exact test names, exact assertion text), complete (covers replacement, deletion, suite-green, lint), and mechanically verifiable. No builder improvisation needed.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 verified) — no deduction
- Lint violations in scope: 0 — no deduction
- AC quality (5/5): no deduction
- Reviewer evidence: present, detailed, 3-cycle with .98 PASS — no deduction
- Full-suite failures in task scope: 0 — no deduction

### Confidence: .98
### Action: archive

### Commit Verification
- `1825ed4e` — `test: replace split-column assertions with unified status column (#797, test-writer)` — confirmed via git log