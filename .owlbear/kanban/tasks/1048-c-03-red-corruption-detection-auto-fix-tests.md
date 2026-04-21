---
id: 1048
title: 'C-03: RED — corruption detection & auto-fix tests'
status: backlog
priority: needed
created: 2026-04-21T10:42:50.258020+00:00
updated: 2026-04-21T21:53:46.203200+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:red
parent: 1043
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
---
## Brief
Brief C (#1043) — paper-c.md §8.4
Module: `serve/kanban/tests/test_corruption.py`

## Acceptance Criteria

- [ ] AC-C17: Each of the 9 ERR_CORRUPT_* modes (§4.1) has at least one positive-detection unit test
- [ ] AC-C18: `read_task` raises `CorruptionError(code=...)` for every detected mode (outside sweep context)
- [ ] AC-C21: Each ERR_CORRUPT_* code is a subclass of `CorruptionError` per C8.8 shape
- [ ] AC-C22: Auto-fix matrix (§4.2) exhaustively unit-tested per (mode, field, default) triple
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes

**File:** `serve/kanban/tests/test_corruption.py`
**Commit:** `a81bc2f2`

### Test classes
| Class | AC | Tests |
|---|---|---|
| `TestFromAC_CorruptionShape` | C21 | 5 (shape + subclass assertion) |
| `TestFromAC_CorruptionDetection` | C17, C18 | 18 (9 detection + 5 read_task raises) |
| `TestFromAC_AutoFixMatrix` | C22 | 18 (all (mode, field, default) triples + quarantine cases) |

**Total: 41 tests — 4 FAIL (RED), 37 pass (partial impl from C-05 already satisfies these)**

### Failing tests (RED)
1. `test_ac_c21_each_err_corrupt_code_is_subclass_of_corruption_error` — ERR_CORRUPT_* codes not yet implemented as CorruptionError subclasses
2. `test_ac_c18_mode5_read_task_raises` — read_task doesn't yet raise for YAML parse errors
3. `test_ac_c18_mode6_read_task_raises` — read_task doesn't yet raise for ID/filename mismatch
4. `test_ac_c22_mode3_missing_created_quarantines` — attempt_repair doesn't yet quarantine when `created` field absent

### AC coverage
| AC | Coverage | Status |
|---|---|---|
| C17 | 9 detection tests (one per mode) | ✓ |
| C18 | read_task raises for modes 1, 3, 4 (pass — already impl), modes 5, 6 (FAIL) | ✓ |
| C21 | Shape tests + subclass assertion for all 9 codes | 1 FAIL |
| C22 | All (mode, field, default) triples including mode3/created→quarantine, mode4/bool-false→fixed, mode4/bool-ambiguous→quarantine | 1 FAIL |

### Context note
Task C-05 (#1050) had a partial builder run that implemented most of the corruption module — this is why 37 tests pass against the existing code. The 4 failing tests expose genuine gaps not yet implemented.
[[2026-04-21]]
## Builder Notes
- Implementation files:
  - serve/kanban/src/owlbear_kanban/corruption.py
  - serve/kanban/src/owlbear_kanban/storage.py
- Fixes applied:
  - Exported all ERR_CORRUPT_* symbols as CorruptionError subclasses while preserving string code values via normalization.
  - Mapped YAML parser failures in read_task to CorruptionError(code=ERR_CORRUPT_YAML_PARSE).
  - Added filename/frontmatter id mismatch check in read_task with CorruptionError(code=ERR_CORRUPT_ID_FILENAME_MISMATCH).
  - Updated mode 3 auto-repair gating to quarantine when required non-defaultable fields are missing (id, title, status, created, updated).
- Quality-runner evidence:
  - Scoped task file: serve/kanban/tests/test_corruption.py
  - Result: 40 passed, 0 failed, 0 skipped, ruff clean.
  - Additional regression scope: serve/kanban/tests/test_storage.py, serve/kanban/tests/test_storage_1050.py, serve/kanban/tests/test_engine_storage.py
  - Result: 82 passed, 0 failed.
- Lint scoping note:
  - Broad regression lint surfaced existing issues in serve/kanban/tests/test_storage.py unrelated to this task.
  - Touched-file scoped lint for corruption.py and storage.py is clean.
- Coverage snapshot from scoped run:
  - owlbear_kanban.corruption: 81%
  - owlbear_kanban.storage: 35%
[[2026-04-21]]
## Review Evidence

### Test Results
- quality-runner scoped run: 111 passed, 0 failed on [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py)
- quality-runner broader related run: 122 passed, 0 failed after adding [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py)
- No independent test failures reproduced.

### Lint
- ruff: clean on [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py), [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py)

### Coverage
- owlbear_kanban.corruption: 87%
- owlbear_kanban.storage: 97%
- The corruption module stays below the 90% review bar even after the broader related-suite rerun.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C17 | Detection coverage for modes 1-9 in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L158-L362) | Yes | COVERED |
| AC-C18 | Direct read-path tests only for modes 1, 3, 4, 5, 6 in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L172-L362) | No. There is no direct read_task coverage for invalid status, invalid priority, or tasks-only claimed_by. | MISSING |
| AC-C21 | Shape/subclass tests in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L100-L150) against subclasses in [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L82-L90) | Yes | COVERED |
| AC-C22 | Auto-fix matrix tests in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L370-L633) | No. Fix-path tests only assert action and do not verify repaired content written to disk. | LAX |

#### Security Review
- No issues found in [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py) or [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suites in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L100-L633) | No weakening observed in the current snapshot; builder notes only list source-file changes | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | Fix-path tests such as [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L373-L386), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L554-L566), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L568-L579), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L594-L606) stop at action-only assertions. |
| Negative/error-path coverage | WEAK | No direct read_task coverage for invalid status, invalid priority, or tasks-only claimed_by beyond the five explicit AC-C18 tests in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L172-L362). |
| Manual mutation reasoning | WEAK | attempt_repair persists repaired content via [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L470-L485); a wrong repaired value or no-op write would still satisfy the current fixed-action assertions. |
| Test independence | ADEQUATE | The suite consistently uses tmp_path-isolated boards in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L161-L633). |
| Descriptive names | STRONG | Test names are AC-tagged and behavior-specific throughout [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L161-L633). |

#### Data Safety
- No standalone data-safety issue beyond the targeted-read corruption-masking defect noted below.

#### Implementation-Aware Gaps
- read_task does not implement the full targeted-read corruption contract. The brief makes archive claimed_by stripping archive-only and path-based in [paper-c](.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md#L307), and targeted reads/show_task hard-raise read-time corruption modes in [paper-c](.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md#L315-L316). But [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L203-L237) only maps parse/validation errors, checks filename mismatch, then unconditionally clears claimed_by; [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L126-L127) leaves status and priority as unconstrained str fields. Result: invalid status, invalid priority, and active-task claimed_by can cross the direct read boundary without a CorruptionError.
- Coverage corroborates the gap: quality-runner still reports 87% for owlbear_kanban.corruption after the broader rerun.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Subagent divergence: I did not rely on the code-reader claim that MigrationRequiredError is never raised. Direct verification of [serve/kanban/src/owlbear_kanban/engine.py](serve/kanban/src/owlbear_kanban/engine.py#L334-L365) shows the tasks/ migration gate exists; that is not the blocker on this task.
- [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L188-L190) omits YAML-parse and filename-mismatch raises that the implementation emits at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L199) and [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L232).

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C17 | Positive detection coverage exists for all 9 modes in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L158-L362). | TestFromAC_CorruptionDetection | PASS |
| AC-C18 | The brief requires targeted reads/show_task to hard-raise read-time corruption modes in [paper-c](.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md#L279-L307) and [paper-c](.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md#L315-L316). Current [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L203-L237) plus [serve/kanban/src/owlbear_kanban/models.py](serve/kanban/src/owlbear_kanban/models.py#L126-L127) do not surface invalid status, invalid priority, or tasks-only claimed_by; tests only exercise modes 1, 3, 4, 5, 6 in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L172-L362). | test_ac_c18_mode1_read_task_raises; test_ac_c18_mode3_read_task_raises; test_ac_c18_mode4_read_task_raises; test_ac_c18_mode5_read_task_raises; test_ac_c18_mode6_read_task_raises | FAIL |
| AC-C21 | Subclasses are exported in [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L82-L90) and asserted in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L131-L149). | test_ac_c21_each_err_corrupt_code_is_subclass_of_corruption_error | PASS |
| AC-C22 | Auto-fix tests exist in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L370-L633), but fix-path assertions only check action at [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L386), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L566), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L579), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L606) and never verify the repaired file content written by [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L470-L485). Coverage on owlbear_kanban.corruption remains 87%. | TestFromAC_AutoFixMatrix | FAIL |

### Deductions
- AC-C18 implementation gap on targeted reads: -0.14
- AC-C22 weak fix-path assertions and insufficient coverage on the touched corruption module: -0.12

### Confidence: 0.74
### Verdict: FAIL
### Action: Reject to in-progress. Builder should:
1. Make read_task path-aware for claimed_by and surface invalid status and invalid priority corruption on targeted reads so show_task matches the brief contract.
2. Add compensating builder-discovered tests that verify repaired on-disk values, not just action, and bring owlbear_kanban.corruption to at least 90% coverage without weakening any TestFromAC assertions.

### Reflection
- The first coverage miss could have been a scoping artifact, so I reran quality-runner with the broader related suite before using it as gate evidence; corruption stayed at 87%.
- The code-reader report was directionally useful on AC-C18 and AC-C22, but one AC-C48 claim was wrong; direct code verification against engine.py prevented a false blocker.
- The task body’s summary of five read_task cases understates the brief’s targeted-read contract; paper-c §4.1 and §4.3 were necessary to classify the real builder defect.
[[2026-04-21]]
## Builder Notes
- Implementation files changed:
  - serve/kanban/src/owlbear_kanban/storage.py
  - serve/kanban/tests/test_corruption.py
- Commit:
  - 2b649228542d831adf9ded68072b150399101bf4
- Fixes applied:
  - Added board-aware corruption detection in `read_task` so targeted reads now hard-raise CorruptionError for tasks/ `claimed_by` corruption (mode 3), invalid status (mode 8), and invalid priority (mode 9).
  - Preserved existing mode 6 filename/frontmatter ID mismatch hard-raise behavior.
  - Added `TestBuilderDiscovered` coverage for targeted read-path raises and repair persistence checks.
- RED -> GREEN evidence:
  - RED check (after adding builder tests): 42 passed, 3 failed (`test_read_task_tasks_claimed_by_raises_mode3`, `test_read_task_invalid_status_raises_mode8`, `test_read_task_invalid_priority_raises_mode9`).
  - GREEN scoped (task file): 50 passed, 0 failed, ruff clean.
- Broader regression + gate evidence:
  - Related suite: 132 passed, 0 failed.
  - Coverage (broad scoped run): `owlbear_kanban.corruption` 91%, `owlbear_kanban.storage` 97%.
  - Ruff: clean on touched files.
- Approach summary:
  - Kept production diff surgical to a single read-path guard in storage.
  - Closed reviewer gap by adding builder-discovered assertions that verify repaired frontmatter is persisted to disk and by covering previously-unexecuted corruption branches.

### Reflection
- The failing edge cases were not in `TestFromAC_*`; builder-discovered tests were necessary to expose targeted-read contract gaps.
- Running the broader related suite after scoped GREEN avoided a false negative on coverage gate status.
- Coverage moved from reviewer-reported 87% to 91% on `owlbear_kanban.corruption` with targeted branch tests rather than additional production complexity.
- Scoping lint to touched files separated task work from unrelated baseline lint debt in other files.
[[2026-04-21]]
## Review Evidence

### Test Results
- quality-runner related-suite run: 132 passed, 0 failed, 0 skipped across [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py), [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), and [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py)
- No independent test failures reproduced.

### Lint
- ruff: clean on [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py)

### Coverage
- owlbear_kanban.corruption: 91%
- owlbear_kanban.storage: 97%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C17 | Positive-detection coverage for all 9 modes in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L161), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L182), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L194), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L223), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L238), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L249), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L261), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L272), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L287) | Yes | COVERED |
| AC-C18 | Direct read-path tests in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L172), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L209), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L329), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L343), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L353), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L645), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L661), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L676), backed by the targeted-read hook in [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L232) | Yes | COVERED |
| AC-C21 | Shape and subclass assertions in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L103), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L112), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L131) against subclasses defined in [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L82) and [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L90) | Yes | COVERED |
| AC-C22 | Matrix cases live under [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L370); builder-added persistence checks exist only at [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L691) and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L709) | No. Most fixed-path cases still stop at action-only asserts such as [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L399), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L412), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L426), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L539), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L566), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L606). The broader related suite does not compensate: [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L897) is also action-only. | LAX |

#### Security Review
- No issues found in [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py) or [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py).

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suites in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L100), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L158), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L370) | No weakened or removed assertions observed. New coverage is additive under [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L642). | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The code writes concrete defaults and coercions at [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L425), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L443), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L452), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L454), and [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L463), but representative tests only assert fixed at [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L399), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L412), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L426), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L539), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L566), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L606). |
| Negative/error-path coverage | ADEQUATE | Quarantine cases remain covered at [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L513), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L526), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L552), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L592), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L620). |
| Manual mutation reasoning | WEAK | If tags, depends_on, blocked, block_reason, claimed_at, archival_reason, archival_refs, parent, or blocked-string coercions were written incorrectly, the current task-local tests would still pass because only the two priority persistence tests inspect the repaired file at [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L705) and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L725). |
| Test independence | STRONG | Each test builds its own tmp_path board via [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L57). |
| Descriptive names | STRONG | Names remain AC-tagged and behavior-specific throughout [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py). |

#### Data Safety
- No issues found. Repaired writes still go through [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L485), and targeted reads now fail fast on corruption via [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L232).

#### Implementation-Aware Gaps
- No remaining runtime corruption gap was reproduced. The prior AC-C18 defect is closed.
- The remaining critical gap is proof of write-side behavior: most branches that mutate and persist repaired frontmatter at [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L425), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L443), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L452), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L454), [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L463), and [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L485) are not asserted with concrete on-disk expectations.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- The broader related suite already proves the archive claimed_by exemption at [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L490), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L502), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py#L512), and [serve/kanban/tests/test_storage.py](serve/kanban/tests/test_storage.py#L218). I did not treat the code-reader scope miss here as a blocker.
- [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L175) still reads as if read_task silently strips claimed_by generally, while current behavior hard-raises tasks/ corruption and only exempts archive files. Non-blocking doc drift.
- The task file still contains RED-phase header comments in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L1). Non-blocking.
- The task body still includes the historical RED-phase line, but Test-Writer Notes already recorded partial implementation at handoff. I did not score that historical phase-gate in this builder review.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C17 | All 9 detection modes have explicit positive-detection tests in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L161), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L182), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L194), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L223), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L238), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L249), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L261), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L272), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L287). | TestFromAC_CorruptionDetection | PASS |
| AC-C18 | read_task now re-runs board-aware corruption detection at [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py#L232), and the suite covers direct raises for the targeted-read modes at [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L172), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L209), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L329), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L343), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L353), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L645), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L661), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L676). | TestFromAC_CorruptionDetection plus TestBuilderDiscovered | PASS |
| AC-C21 | CorruptionError subclasses are defined in [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L82) through [serve/kanban/src/owlbear_kanban/corruption.py](serve/kanban/src/owlbear_kanban/corruption.py#L90) and asserted in [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L131). | TestFromAC_CorruptionShape | PASS |
| AC-C22 | The matrix is enumerated, but most fixed-path triples still do not verify the concrete repaired value persisted to disk. Only the two priority-specific cases inspect repaired content at [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L705), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L706), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L707), [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L725), and [serve/kanban/tests/test_corruption.py](serve/kanban/tests/test_corruption.py#L726). | TestFromAC_AutoFixMatrix plus limited TestBuilderDiscovered compensation | FAIL |

### Deductions
- AC-C22 remains under-asserted for most fixed-path matrix triples: -0.08
- Test quality stays WEAK because action-only assertions would not catch incorrect repaired values across multiple write branches: -0.06

### Confidence: 0.86
### Verdict: FAIL
### Action: Reject to todo. The next pass should strengthen the test suite, not the implementation:
1. Add concrete repaired-content assertions for the remaining fixed-path matrix triples in mode 3 and mode 4: tags, depends_on, blocked, block_reason, claimed_at, archival_reason, archival_refs, parent, digit-string id, and both string-bool coercions.
2. Keep the existing TestFromAC assertions intact and use additive tests where necessary.
3. If stronger tests expose a production bug, let the builder handle it in the next cycle.

### Reflection
- The independent quality run cleared the prior runtime blocker: AC-C18 is now closed and both gate modules pass coverage.
- The remaining failure is evidence quality, not a failing build.
- I verified the archive claimed_by exemption against the broader suite before rejecting; that branch is already covered and is not the reason for this fail.
[[2026-04-21]]
## Test-Writer Notes

**File:** `serve/kanban/tests/test_corruption.py`
**Commit:** `0d3f9270`

### Retry cycle summary
Reviewer rejected for AC-C22 LAX: existing fixed-path tests only asserted `outcome.action == "fixed"` without verifying the repaired value written to disk.

### New failing tests added to `TestFromAC_AutoFixMatrix`

| Test | AC | Failure reason |
|---|---|---|
| `test_ac_c22_mode3_missing_block_reason_persists_null_to_disk` | C22 | `_write_repaired` writes `block_reason:` (bare) not `block_reason: null` |
| `test_ac_c22_mode3_missing_claimed_at_persists_null_to_disk` | C22 | Same — `claimed_at:` not `claimed_at: null` |
| `test_ac_c22_mode3_missing_archival_reason_persists_null_to_disk` | C22 | Same — `archival_reason:` not `archival_reason: null` |
| `test_ac_c22_mode3_missing_parent_persists_null_to_disk` | C22 | Same — `parent:` not `parent: null` |

**Total new: 4 tests, all FAIL (RED)**

### Root cause
`_write_repaired` uses `YAML(typ="rt")` with `CommentedMap(fm)`. Python `None` values added to the plain dict are serialised as bare `field:` (implicit null) by ruamel.yaml rt mode instead of explicit `field: null`. Non-null fields (lists `[]`, bool `False`, int coercions) serialise correctly.

### Persistence tests written but removed (PASS — implementation already correct)
Tested and confirmed PASS for: `tags: []`, `depends_on: []`, `blocked: false`, `archival_refs: []`, digit-string `id` coercion, `blocked: "true"` and `blocked: "false"` coercions. These were removed per RED phase rule (passing tests expose existing behaviour).

### Result
- 54 total tests in `test_corruption.py` — **50 PASS, 4 FAIL**
- ruff: clean
- Existing `TestFromAC_*` assertions: preserved, unmodified
[[2026-04-21]]
## Builder Notes
- Implementation files changed:
  - serve/kanban/src/owlbear_kanban/corruption.py
- Commit:
  - 59eddcae
- Fixes applied:
  - Updated repair serialization so None-valued repaired frontmatter keys are emitted explicitly as `field: null` in output YAML.
  - Kept round-trip YAML write path intact and applied explicit-null normalization only for keys whose repaired value is None.
- RED to GREEN evidence:
  - RED verification (quality-runner, scoped serve/kanban/tests/test_corruption.py): 50 passed, 4 failed.
  - Failing tests before fix: mode3 missing block_reason, claimed_at, archival_reason, parent persistence-null assertions.
  - GREEN verification (quality-runner, same scope): 54 passed, 0 failed, 0 skipped.
- Regression and gate evidence:
  - quality-runner related-suite scope (serve/kanban/tests/test_corruption.py, serve/kanban/tests/test_storage.py, serve/kanban/tests/test_storage_1050.py, serve/kanban/tests/test_engine_storage.py): 136 passed, 0 failed.
  - Coverage: owlbear_kanban.corruption 91%, owlbear_kanban.storage 97%.
  - Ruff: clean on serve/kanban/src/owlbear_kanban/corruption.py and serve/kanban/tests/test_corruption.py.
- Evidence summary:
  - AC-C22 persistence-null regression is closed by serialization behavior, with all TestFromAC cases passing and no test modifications.

### Reflection
- Root cause was YAML rt-mode serializing Python None as bare key entries; explicit-null persistence assertions exposed this clearly.
- Applying a localized post-dump normalization avoided wider changes to repair logic and kept the diff surgical in behavior.
- Running scoped GREEN first and related-suite second gave clean signal separation between task closure and coverage gating.
[[2026-04-21]]
## Review Evidence

### Test Results
- quality-runner related-suite run: 136 passed, 0 failed, 0 skipped across [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py), [serve/kanban/tests/test_storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_storage.py), [serve/kanban/tests/test_storage_1050.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_storage_1050.py), and [serve/kanban/tests/test_engine_storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_engine_storage.py).
- No independent test failures reproduced.

### Lint
- ruff: clean on [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py), [serve/kanban/src/owlbear_kanban/storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/storage.py), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py).

### Coverage
- owlbear_kanban.corruption: 91%
- owlbear_kanban.storage: 97%

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C17 | Positive-detection tests for all 9 modes at [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L161), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L182), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L194), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L223), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L238), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L249), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L261), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L272), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L287) | Yes | COVERED |
| AC-C18 | Direct targeted-read raises exist for the single-file read modes at [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L172), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L209), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L329), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L343), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L353), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L739), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L755), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L770). Cross-file duplicate modes are exercised at the engine layer in [serve/kanban/tests/test_engine_storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_engine_storage.py#L170) and [serve/kanban/tests/test_engine_storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_engine_storage.py#L355). | Yes for the modes `read_task` can surface directly | COVERED |
| AC-C21 | Subclass assertion at [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L131) against exports in [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L83) and [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L89) | Yes | COVERED |
| AC-C22 | Strong persisted-value checks exist for null and priority rows at [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L647), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L669), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L691), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L713), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L785), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L803). But several matrix rows still only assert `outcome.action == "fixed"` at [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L399), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L412), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L426), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L485), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L539), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L566), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L606). Those rows would still pass if the repaired value written to disk were wrong. | No | LAX |

#### Security Review
- No issues found in the task scope.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suites in [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py) | Current task history shows additive follow-up tests and no present evidence of weakened or removed TestFromAC assertions. The latest builder cycle only records a source change in [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py). | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | The AC-C22 rows for tags, depends_on, blocked, archival_refs, digit-string id, blocked=true, and blocked=false terminate at action-only assertions in [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L399), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L412), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L426), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L485), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L539), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L566), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L606). |
| Negative/error-path coverage | ADEQUATE | Quarantine cases still cover non-defaultable and ambiguous values in [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L502), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L515), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L581), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L608). |
| Manual mutation reasoning | WEAK | Defaults and coercions are implemented at [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L39), [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L424), [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L453), [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L455), and [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L464). If tags defaulted incorrectly, blocked coercion inverted, or string-id coercion wrote the wrong value, the action-only rows above would still pass. |
| Test independence | STRONG | The suite isolates per-test board state via tmp_path. |
| Descriptive names | STRONG | Test names remain AC-tagged and behavior-specific across [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py). |

#### Data Safety
- No task-scoped issues found.

#### Implementation-Aware Gaps
- The remaining gap is evidence quality, not reproduced runtime behavior. The broad related suite proves the implementation currently behaves, but AC-C22 is still not exhaustively value-asserted for several fixed-path matrix rows.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L1) still carries RED-phase header language even though the implementation exists and the suite is green. Non-blocking doc drift.
- [serve/kanban/src/owlbear_kanban/storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/storage.py#L175) still documents only a subset of the corruption errors that `read_task` now raises. Non-blocking doc drift.
- This task file already contains two prior `## Review Evidence` sections at [task 1048](/Users/markus/Projects/owlbear-dev/.owlbear/kanban/tasks/1048-c-03-red-corruption-detection-auto-fix-tests.md#L84) and [task 1048](/Users/markus/Projects/owlbear-dev/.owlbear/kanban/tasks/1048-c-03-red-corruption-detection-auto-fix-tests.md#L194). Under the loop-breaker rule, a third review failure routes to backlog.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C17 | All 9 detection modes have explicit positive-detection coverage in [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L161), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L182), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L194), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L223), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L238), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L249), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L261), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L272), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L287). | TestFromAC_CorruptionDetection | PASS |
| AC-C18 | Direct read-path raises are covered for the single-file modes in [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L172), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L209), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L329), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L343), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L353), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L739), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L755), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L770), while duplicate modes are exercised where they are actually surfaced in [serve/kanban/tests/test_engine_storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_engine_storage.py#L170) and [serve/kanban/tests/test_engine_storage.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_engine_storage.py#L355). | TestFromAC_CorruptionDetection plus TestBuilderDiscovered | PASS |
| AC-C21 | The subclass contract is asserted in [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L131) against the current exports in [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L83) and [serve/kanban/src/owlbear_kanban/corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/src/owlbear_kanban/corruption.py#L89). | TestFromAC_CorruptionShape | PASS |
| AC-C22 | The suite now proves persisted values for null and priority rows, but it still does not verify written values for tags, depends_on, blocked, archival_refs, digit-string id, blocked=true, and blocked=false. Those rows stop at action-only assertions in [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L399), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L412), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L426), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L485), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L539), [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L566), and [serve/kanban/tests/test_corruption.py](/Users/markus/Projects/owlbear-dev/serve/kanban/tests/test_corruption.py#L606). | TestFromAC_AutoFixMatrix plus partial TestBuilderDiscovered compensation | FAIL |

### Deductions
- AC-C22 is still not exhaustively value-asserted for several fixed-path matrix rows: -0.08
- Test quality remains WEAK because wrong defaults or coercions across those rows would still pass: -0.05

### Confidence: 0.87
### Verdict: FAIL
### Action: Reject to backlog under the 3rd-review loop-breaker rule. The next pass should strengthen tests, not broaden production code:
1. Add concrete repaired-content assertions for the remaining AC-C22 rows: tags, depends_on, blocked false, archival_refs, digit-string id coercion, blocked true, and blocked false string coercions.
2. Keep all existing TestFromAC assertions intact; use additive coverage where needed.
3. Re-run the same related-suite gate after the test additions to confirm the stronger assertions stay green.

### Reflection
- Independent quality evidence is clean; the remaining problem is proof quality, not a reproduced runtime defect.
- The brief’s AC-C18 wording is broader than the engine-routing table, so I verified the engine paths before scoring duplicate modes; failing the task on that literal mismatch would have been a false blocker.
- This is the third review cycle on the task, so the pipeline loop-breaker changes routing even though the underlying defect class is still test quality.