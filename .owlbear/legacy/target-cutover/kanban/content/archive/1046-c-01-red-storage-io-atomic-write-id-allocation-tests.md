---
id: 1046
title: 'C-01: RED — storage_io atomic-write & ID-allocation tests'
status: archived
priority: medium
created: 2026-04-21T10:42:50.236472+00:00
updated: 2026-04-22T19:03:11.034317+00:00
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
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §8.1, §8.11
Module: `serve/kanban/tests/test_storage_io.py`

## Acceptance Criteria

- [ ] AC-C1: `atomic_write(target, content)` writes to `.tmp-*` sibling, fsyncs, replaces, fsyncs parent dir on POSIX
- [ ] AC-C2: `atomic_write` cleans up `.tmp-*` on exception; target unaffected. Simulated `os.replace` failure
- [ ] AC-C3: `list_task_files` filters out `.tmp-*` files
- [ ] AC-C4: `allocate_next_id` holds `.next_id.lock` during read+increment+save. Concurrent test: 50 threads × 1 ID → 50 distinct IDs
- [ ] AC-C4a: `write_task_if_unchanged` CAS test: 20 threads racing → exactly 1 success, 19 `ERR_STALE`; survivor write intact
- [ ] AC-C4b: Lock files at `tasks/.<id>.lock`, gitignored, never returned by `list_task_files`/`list_archive_files`, never quarantined
- [ ] AC-C51: ID burn on crash: simulate crash between `save_config` and `write_task` → next `create_task` allocates `original_next_id + 2`
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes
- Test file: `serve/kanban/tests/test_storage_io.py`
- Classes: `TestFromAC_AtomicWrite`, `TestFromAC_IDAllocation`
- Tests per category: happy 3, edge 2, error 4, boundary/concurrency 3
- Total: 12 tests
- ruff: clean

**Pipeline history note:** Tests were written and committed in RED state (commit `de06fa41`, before implementation) — verified by `git log`. The implementation was subsequently added (commit `ac7cb6e1 feat(kanban): add storage surface`). All 12 tests are now GREEN (passing). Task was never formally advanced after the builder completed GREEN phase.

**AC coverage:**
| AC | Test(s) |
|----|---------|
| C1 — tmp sibling, fsync, replace | `test_ac_c1_writes_via_tmp_sibling`, `test_ac_c1_posix_fsyncs_file_and_dir`, `test_ac_c1_final_content_is_correct` |
| C2 — cleanup on exception | `test_ac_c2_cleans_up_tmp_on_replace_failure`, `test_ac_c2_target_unaffected_on_fsync_failure` |
| C3 — list_task_files excludes .tmp- | `test_ac_c3_list_task_files_excludes_tmp` |
| C4 — 50 distinct IDs (concurrent) | `test_ac_c4_50_concurrent_threads_yield_distinct_ids` |
| C4a — CAS: 1 success / 19 ERR_STALE | `test_ac_c4a_cas_20_threads_one_success_19_stale`, `test_ac_c4a_survivor_write_intact` |
| C4b — lock files excluded from list_task_files/list_archive_files | `test_ac_c4b_lock_files_not_in_list_task_files`, `test_ac_c4b_lock_files_not_in_list_archive_files` |
| C51 — ID burn on crash | `test_ac_c51_crash_between_save_config_and_write_task` |

**Coverage gap note:** AC-C4b "never quarantined" has no explicit test. The implementation satisfies this implicitly (corruption scanner uses `glob("*.md")` — lock files have `.lock` extension). A regression guard test trivially passes with current impl, so no RED test is possible; recommend test-curator add a regression guard post-archive.

Advancing to in-progress (GREEN phase already complete).
[[2026-04-21]]
## Builder Notes
- Implementation: No code changes in this retry/formalization step (existing implementation already present from prior GREEN work).
- Tests: 12 `TestFromAC_*` passed in `serve/kanban/tests/test_storage_io.py`; 0 `TestBuilderDiscovered` added in this step.
- Coverage: 77% on `owlbear_kanban.storage` from scoped verification run.
- Ruff: clean for `serve/kanban/src/owlbear_kanban/storage.py` and `serve/kanban/tests/test_storage_io.py`.
- Evidence summary: Independent quality-runner verification shows `failed: []`, `pytest: 0`, and `ruff: 0` for task-scoped checks.
- Post-task reflection:
  - Problem faced: Task had already reached GREEN previously but remained in `in-progress` without formal status advance.
  - Workaround applied: Re-ran scoped quality-runner checks to produce fresh, canonical evidence before transition.
  - Pattern discovered: Retroactive formalization tasks benefit from explicit re-verification to avoid stale evidence.
  - Time sink: None beyond verification pass.
  - Quality gap: Module-wide coverage is below the typical 90% gate in this scoped run (77%), despite AC test set being fully green.
[[2026-04-21]]
## Review Evidence
### Test Results
- Quality-Runner scoped rerun: 12 passed, 0 failed, 0 skipped for serve/kanban/tests/test_storage_io.py.

### Lint
- Clean for serve/kanban/src/owlbear_kanban/storage.py, serve/kanban/src/owlbear_kanban/storage_io.py, and serve/kanban/tests/test_storage_io.py.

### Coverage
- owlbear_kanban.storage: 77%
- owlbear_kanban.storage_io: 100%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C1 | test_ac_c1_* | No. serve/kanban/tests/test_storage_io.py:127 only checks `len(fsync_calls) >= 2`, not that the second fsync is the parent dir; the basename check at lines 102-110 does not prove the temp file stayed in the sibling directory. | LAX |
| AC-C2 | test_ac_c2_* | No for the post-replace dir-fsync branch. serve/kanban/tests/test_storage_io.py:160-166 only forces failure on the first fsync, but serve/kanban/src/owlbear_kanban/storage_io.py:44-49 can still raise after the target was already replaced. | LAX |
| AC-C3 | test_ac_c3_list_task_files_excludes_tmp | Yes. serve/kanban/src/owlbear_kanban/storage.py:319-329 excludes hidden/temp files and serve/kanban/tests/test_storage_io.py:172-183 rejects `.tmp-` entries. | COVERED |
| AC-C4 | test_ac_c4_50_concurrent_threads_yield_distinct_ids | Partially. The outcome is covered, but the test does not directly prove the `.next_id.lock` critical section at serve/kanban/src/owlbear_kanban/storage.py:386-392. | LAX |
| AC-C4a | test_ac_c4a_* | Yes for one success, 19 `ERR_STALE`, and survivor readback at serve/kanban/tests/test_storage_io.py:220-291. | COVERED |
| AC-C4b | test_ac_c4b_* | No. The scoped tests only cover list exclusion at serve/kanban/tests/test_storage_io.py:293-317; they do not cover gitignore or never-quarantined clauses. | MISSING |
| AC-C51 | test_ac_c51_crash_between_save_config_and_write_task | No. The test at serve/kanban/tests/test_storage_io.py:319-336 asserts next allocation equals `original_next_id + 1` and never calls `create_task`, while the task body and .owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:747 require the next `create_task` to allocate `original_next_id + 2`. | MISSING |

#### Security Review
- No shell, SQL, deserialization, or secret-handling issues found in the scoped files.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_AtomicWrite | Current snapshot still contains AC-specific tests; no `skip` or `xfail` markers observed. | PRESERVED (current snapshot only) |
| TestFromAC_IDAllocation | Current snapshot still contains AC-specific tests; no `skip` or `xfail` markers observed. | PRESERVED (current snapshot only) |
- Historical immutability against the earlier RED commit was not independently re-verified with the available tool set.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | serve/kanban/tests/test_storage_io.py:127 only checks fsync call count; the survivor check at line 291 only asserts title equality. |
| Negative and error-path coverage | WEAK | No test covers parent-directory fsync failure after replace even though serve/kanban/src/owlbear_kanban/storage_io.py:44-49 can raise after the target changed. |
| Manual mutation resistance | WEAK | A wrong second-fsync target or wrong AC-C51 crash contract would still pass the current suite. |
| Test independence | STRONG | Each case builds an isolated temp board with `_make_board`. |
| Descriptive names | STRONG | Test names are AC-specific throughout the file. |

#### Data Safety
- AC-C2 is broken in code: serve/kanban/src/owlbear_kanban/storage_io.py:44 replaces the target before the parent-dir fsync at lines 46-49, and cleanup at line 54 only unlinks the old temp path. If the dir fsync raises, the call fails after the target already changed, which violates “target unaffected on exception”.
- AC-C4b is broken in code and config: per-task lock files live at serve/kanban/src/owlbear_kanban/storage.py:299, but .gitignore:108 and seed/.gitignore:68 only ignore `.owlbear/kanban/.next_id.lock`. There is no ignore rule for `tasks/.<id>.lock`.
- AC-C4b never-quarantined is not guaranteed by the public API: serve/kanban/src/owlbear_kanban/storage.py:368-373 will move any supplied path, including a lock file.

#### Implementation-Aware Gaps
- serve/kanban/src/owlbear_kanban/corruption.py:505 and 510 only scan `*.md`, so lock files are skipped by the corruption scanner today, but there is no explicit regression guard for the never-quarantined clause.
- No `TestBuilderDiscovered` tests compensate for the lax or missing AC coverage above.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- serve/kanban/tests/test_storage_io.py:1-5 still describes the file as an all-failing RED suite even though the current snapshot is green.
- `owlbear_kanban.storage` coverage is 77%, below the usual 90% module gate, though this is not the primary blocker.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C1 | serve/kanban/src/owlbear_kanban/storage_io.py:34-49 implements the sequence, but the tests do not fully constrain sibling path or parent-dir fsync. | test_ac_c1_* | PASS |
| AC-C2 | serve/kanban/tests/test_storage_io.py only covers pre-replace failures; serve/kanban/src/owlbear_kanban/storage_io.py:44-49 allows a post-replace exception with changed target. | test_ac_c2_* | FAIL |
| AC-C3 | `list_task_files` filters hidden/temp files at serve/kanban/src/owlbear_kanban/storage.py:319-329; the scoped test passes at serve/kanban/tests/test_storage_io.py:172-183. | test_ac_c3_list_task_files_excludes_tmp | PASS |
| AC-C4 | `allocate_next_id` locks `.next_id.lock` around load, increment, and save at serve/kanban/src/owlbear_kanban/storage.py:386-392; the 50-thread uniqueness test passes. | test_ac_c4_50_concurrent_threads_yield_distinct_ids | PASS |
| AC-C4a | `write_task_if_unchanged` locks `tasks/.<id>.lock` at serve/kanban/src/owlbear_kanban/storage.py:299 and enforces `ERR_STALE` at lines 307-311; the race tests pass. | test_ac_c4a_* | PASS |
| AC-C4b | Tests only cover listing exclusion. No gitignore rule exists for `tasks/.<id>.lock`, and `move_to_quarantine` can still move a lock file. | test_ac_c4b_* | FAIL |
| AC-C51 | The task body and .owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:747 require next `create_task` equals `original_next_id + 2`; serve/kanban/tests/test_storage_io.py:319-336 asserts next `allocate_next_id` equals `original_next_id + 1`. | test_ac_c51_crash_between_save_config_and_write_task | FAIL |
| RED-phase history gate | Current review did not independently re-run git-history verification for the earlier RED commit referenced in the task body. | historical task note only | N/A |

### Deductions
- 0.18 AC-C2 fails on the post-replace dir-fsync exception path.
- 0.16 AC-C4b is neither fully implemented nor fully covered.
- 0.12 AC-C51 contradicts the task body and brief.
- 0.08 Test quality is weak for AC-C1 and AC-C2.
- 0.04 `owlbear_kanban.storage` coverage is below the usual module gate.

### Confidence: 0.37
### Verdict: FAIL
### Action
Reject to backlog. This task now has both builder defects (AC-C2 and AC-C4b) and test/contract defects (AC-C51 contradiction plus missing AC-C4b evidence). Architect/test-writer need to reconcile the contract first, then builder can return for a clean implementation pass.
[[2026-04-21]]
## Architecture Review

### Previous Cycle Analysis
Reviewer FAIL (confidence 0.37) identified: AC-C2 post-replace dir-fsync gap, AC-C4b gitignore/quarantine missing, AC-C51 +2/+1 mismatch, weak test assertions. Code and tests are correct; the failures stem from AC wording imprecision.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-C1 | PASS — tests verify tmp sibling, fsync calls, final content | None |
| AC-C2 | IMPRECISE — "target unaffected" is ambiguous for post-commit exceptions. `os.replace` is the commit point per Brief C §3.1. Post-replace dir-fsync failure propagates to caller but target correctly contains new content. | **Refined**: `.tmp-*` cleaned up on any exception. Target unaffected when exception occurs before `os.replace` (the commit point). Simulated: `os.replace` failure, pre-replace `fsync` failure. |
| AC-C3 | PASS — list_task_files filters `.tmp-*` | None |
| AC-C4 | PASS — 50-thread concurrent allocation | None |
| AC-C4a | PASS — CAS 20-thread race, survivor intact | None |
| AC-C4b | MIXED — list exclusion tested ✓. "gitignored" is config, not testable Python. "never quarantined" is implicit (corruption scanner uses `*.md` glob). | **Refined**: remove "gitignored, never quarantined" from this task. Split to #1096 (config task). Quarantine implicit guarantee noted for #1057 architect. |
| AC-C51 | WRONG NUMBER — paper-c.md says `+2`, correct math is `+1`. Per §3.3: burn ID N → config at N+1 → next allocate returns N+1 → config ends at N+2. Test correctly asserts `+1`. | **Refined**: next `allocate_next_id` returns `original_next_id + 1`; config ends at `original_next_id + 2` (one ID burned). |
| "All tests fail" | MOOT — RED+GREEN complete | **Removed** from active AC |

### Refined AC (authoritative for downstream agents)

- [ ] AC-C1: `atomic_write(target, content)` writes to `.tmp-*` sibling, fsyncs file fd, `os.replace` to target, fsyncs parent dir fd on POSIX
- [ ] AC-C2: `.tmp-*` cleaned up on any exception. Target unaffected when exception occurs before `os.replace` (the commit point). Simulated: `os.replace` failure, pre-replace `fsync` failure
- [ ] AC-C3: `list_task_files` filters out `.tmp-*` files
- [ ] AC-C4: `allocate_next_id` holds `.next_id.lock` during read+increment+save. Concurrent test: 50 threads × 1 ID → 50 distinct IDs
- [ ] AC-C4a: `write_task_if_unchanged` CAS test: 20 threads racing → exactly 1 success, 19 `ERR_STALE`; survivor write intact
- [ ] AC-C4b: Lock files at `tasks/.<id>.lock`, never returned by `list_task_files`/`list_archive_files`
- [ ] AC-C51: ID burn on crash: simulate crash after `allocate_next_id` bumps config but before `write_task` → next `allocate_next_id` returns `original_next_id + 1`; config ends at `original_next_id + 2` (one ID burned, no task file for burned ID)

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage I/O + ID allocation — cohesive primitives |
| Interface clarity | PASS (after refinement) | AC-C2 commit-point, AC-C51 math now precise |
| Dependency correctness | PASS | No deps; downstream #1055 depends on this |
| Module layering | PASS | storage_io → storage direction correct |
| TDD compliance | PASS | RED task; GREEN counterpart is #1055 |
| KISS/YAGNI | PASS | Minimal scope aligned with Brief C |
| Premise challenge | PASS | Atomic write and ID allocation are core storage primitives |
| Pattern consistency | PASS | flock, atomic_write, ConcurrencyError follow Brief C conventions |
| Security surface | PASS | No external input boundaries |
| Single domain | PASS | kanban storage domain only |

### Engine create_task Order — Cross-Task Note
Engine `create_task` (engine.py:687-690) does `write_task` BEFORE `save_config` — the exact order Brief C §3.3 line 257 explicitly REJECTS. This is pre-Brief C code (#923 era). The storage-level `allocate_next_id` correctly implements save-before-write. The engine must be refactored in #1062 (C-17 GREEN) to use `allocate_next_id` or reverse its inline order. This is NOT blocking for #1046 — it's engine scope.

### Challenge Results
- Challenger: BLOCK (confidence: 0.24)
- Findings: (1) engine create_task uses wrong order, (2) AC-C2 being weakened, (3) AC-C4b split drops traceability, (4) tests don't exercise engine path
- Architect rebuttal: ACCEPTED in part, OVERRIDDEN with justification:
  - (1) Engine order is real defect but scoped to #1062, not #1046. Storage-level `allocate_next_id` is correct. Noted for #1062 architect.
  - (2) AC-C2 is CLARIFIED, not weakened. `os.replace` is the commit point per Brief C §3.1. Post-replace dir-fsync is a durability guarantee. The refinement makes the commit-point semantics explicit rather than leaving them ambiguous.
  - (3) Gitignore is config, not Python. Split to #1096 (`type:config` tagged). GREEN task #1055 architect should similarly refine AC-C4b.
  - (4) Storage_io tests test the storage surface. Engine integration is #1053/#1062 scope. Layer separation is correct.

### Follow-up Tasks
- #1096 (C-01a): gitignore rules for per-task lock files — created at backlog, `type:config` tagged

### Verdict: APPROVE (REFINE + APPROVE)
### Action: AC refined in-place above. Task advanced to todo. Reviewer should evaluate against the refined AC in this section, not the original AC.
[[2026-04-21]]
## Test-Writer Notes
- Retry cycle: reviewer FAIL items (AC-C2, AC-C4b, AC-C51) were resolved by architect's AC refinement — not by missing tests.
- Test file: `serve/kanban/tests/test_storage_io.py`
- Classes: `TestFromAC_AtomicWrite`, `TestFromAC_IDAllocation`
- Total: 12 tests — all **GREEN** (implementation already exists from prior cycle)

**Under refined AC, all AC lines are covered:**
| AC | Test(s) | Status |
|----|---------|--------|
| AC-C1 | `test_ac_c1_*` (3) | COVERED |
| AC-C2 | `test_ac_c2_*` (2) — pre-`os.replace` fsync + `os.replace` failure; refined AC clarifies "before commit point" | COVERED |
| AC-C3 | `test_ac_c3_list_task_files_excludes_tmp` | COVERED |
| AC-C4 | `test_ac_c4_50_concurrent_threads_yield_distinct_ids` | COVERED |
| AC-C4a | `test_ac_c4a_*` (2) | COVERED |
| AC-C4b | `test_ac_c4b_*` (2) — listing exclusion; gitignore/quarantine split to #1096 | COVERED |
| AC-C51 | `test_ac_c51_crash_between_save_config_and_write_task` — asserts `+1` allocation, `+2` config, burned ID has no file | COVERED |

**Why pass-through (not new tests):** Reviewer cited 3 FAIL items (C2, C4b, C51). Architect's AC refinement addressed all three by clarifying semantics — not by demanding new behavior. Existing tests cover the refined AC. Reviewer also cited weak assertion quality (AC-C1 fsync count ≥ 2), which is test-quality scope, not missing coverage.

Pass-through to builder for reviewer re-evaluation against refined AC.
[[2026-04-21]]
## Builder Notes
- Implementation: No code changes in this cycle; existing behavior in serve/kanban/src/owlbear_kanban/storage_io.py and serve/kanban/src/owlbear_kanban/storage.py already satisfies the refined AC in the task body.
- RED verification context: TestFromAC cases are already GREEN before this cycle because implementation landed earlier; investigated via task history and proceeded with re-verification evidence.
- Tests: quality-runner scoped run on serve/kanban/tests/test_storage_io.py reported 12 passed, 0 failed, 0 skipped.
- Regression check: quality-runner module-level run on serve/kanban/tests/test_storage_io.py plus serve/kanban/tests/test_storage.py reported 23 passed, 0 failed, 0 skipped.
- Coverage: owlbear_kanban.storage_io 100 percent; owlbear_kanban.storage 75 percent in task-scoped run and 78 percent in module-level run.
- Ruff: clean on task-scoped lint paths (storage_io.py, storage.py, test_storage_io.py). Module-level run surfaced pre-existing lint debt in serve/kanban/tests/test_storage.py (11 violations), outside this task file.
- Approach: surgical formalization pass only, with canonical quality-runner evidence and no behavioral edits.
- Fixes applied: none.
- Post-task reflection:
  - Problem faced: task state required builder formalization despite prior implementation already merged.
  - Workaround applied: produced fresh scoped and module-level quality evidence instead of changing stable code.
  - Pattern discovered: retroactive builder passes should separate task-scoped lint from background lint debt.
  - Time sink: triaging module-level lint findings unrelated to this task.
  - Quality gap: storage module coverage remains below 90 percent at this scope and may need dedicated test-curation follow-up.
[[2026-04-21]]
## Review Evidence
### Test Results
- Quality-Runner scoped run: 12 passed, 0 failed, 0 skipped for `serve/kanban/tests/test_storage_io.py`.
- Supplemental storage-module run: 72 passed, 0 failed, 0 skipped for `serve/kanban/tests/test_storage_io.py`, `serve/kanban/tests/test_storage.py`, and `serve/kanban/tests/test_storage_1050.py`.

### Lint
- Clean for `serve/kanban/src/owlbear_kanban/storage_io.py`, `serve/kanban/src/owlbear_kanban/storage.py`, and `serve/kanban/tests/test_storage_io.py`.

### Coverage
- `owlbear_kanban.storage_io`: 100%
- `owlbear_kanban.storage`: 96% with related storage tests included (`serve/kanban/tests/test_storage_io.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`)
- Note: task-only scope reports `owlbear_kanban.storage` at 75%, but that undercounts the touched-module coverage because related storage tests live in separate task files.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C1 | `test_ac_c1_writes_via_tmp_sibling`, `test_ac_c1_posix_fsyncs_file_and_dir`, `test_ac_c1_final_content_is_correct` | No. `serve/kanban/tests/test_storage_io.py:100-110` only records the temp basename and `.tmp-` prefix, not sibling placement or replace destination. `serve/kanban/tests/test_storage_io.py:127` only asserts `len(fsync_calls) >= 2`, so double-fsyncing the file fd or using the wrong ordering would still pass. | LAX |
| AC-C2 | `test_ac_c2_cleans_up_tmp_on_replace_failure`, `test_ac_c2_target_unaffected_on_fsync_failure` | Yes. `serve/kanban/tests/test_storage_io.py:142-170` covers replace failure and pre-replace fsync failure with cleanup and unchanged-target assertions, matching the refined commit-point AC. | COVERED |
| AC-C3 | `test_ac_c3_list_task_files_excludes_tmp` | Yes. `serve/kanban/tests/test_storage_io.py:172-183` rejects `.tmp-` entries, matching `serve/kanban/src/owlbear_kanban/storage.py:360-361`. | COVERED |
| AC-C4 | `test_ac_c4_50_concurrent_threads_yield_distinct_ids` | Yes. `serve/kanban/tests/test_storage_io.py:194-218` requires 50 results, 50 distinct IDs, and no errors; `serve/kanban/src/owlbear_kanban/storage.py:418-423` performs load/increment/save under `.next_id.lock`, backed by `serve/kanban/src/owlbear_kanban/engine.py:240-262`. | COVERED |
| AC-C4a | `test_ac_c4a_cas_20_threads_one_success_19_stale`, `test_ac_c4a_survivor_write_intact` | Yes. `serve/kanban/tests/test_storage_io.py:220-291` enforces 1 success / 19 `ERR_STALE` and verifies the survivor write; the implementation locks `tasks/.<id>.lock` and checks staleness at `serve/kanban/src/owlbear_kanban/storage.py:331-342`. | COVERED |
| AC-C4b | `test_ac_c4b_lock_files_not_in_list_task_files`, `test_ac_c4b_lock_files_not_in_list_archive_files` | No for the location clause. `serve/kanban/tests/test_storage_io.py:293-317` hand-creates `.lock` files and only asserts list exclusion; it does not verify that `write_task_if_unchanged` actually uses `tasks/.<id>.lock` as required by `serve/kanban/src/owlbear_kanban/storage.py:331`. | LAX |
| AC-C51 | `test_ac_c51_crash_between_save_config_and_write_task` | Yes. `serve/kanban/tests/test_storage_io.py:319-340` asserts next allocation = original+1, config next_id = original+2, and no burned task file. | COVERED |

#### Security Review
- No issues found in scope. The reviewed code uses local temp files, fsync, rename, and file locks only; no shell execution, unsafe deserialization, secret handling, or new external input surface was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_AtomicWrite` | Current snapshot still contains the AC-specific cases at `serve/kanban/tests/test_storage_io.py:91-183`; no `skip`/`xfail` markers observed. Historical immutability against the earlier RED commit was not independently re-verified with the available tool set. | PRESERVED (current snapshot) |
| `TestFromAC_IDAllocation` | Current snapshot still contains the AC-specific cases at `serve/kanban/tests/test_storage_io.py:191-340`; no `skip`/`xfail` markers observed. Historical immutability against the earlier RED commit was not independently re-verified with the available tool set. | PRESERVED (current snapshot) |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC-C1 only checks basename/prefix at `serve/kanban/tests/test_storage_io.py:100-110` and fsync count at `serve/kanban/tests/test_storage_io.py:127`; AC-C4b only checks listing exclusion at `serve/kanban/tests/test_storage_io.py:293-317`. |
| Negative and error-path coverage | ADEQUATE | AC-C2 replace failure and pre-replace fsync failure are covered at `serve/kanban/tests/test_storage_io.py:136-170`; the stale OCC path is covered at `serve/kanban/tests/test_storage_io.py:220-257`. |
| Manual mutation reasoning | WEAK | Moving temp creation outside `target.parent`, fsyncing the file fd twice instead of fsyncing the parent directory, or changing the CAS lock path outside `tasks/.<id>.lock` would still satisfy the current AC-C1/AC-C4b assertions. |
| Test independence | STRONG | Threaded cases guard shared collectors with `threading.Lock` at `serve/kanban/tests/test_storage_io.py:199`, `serve/kanban/tests/test_storage_io.py:230`, and `serve/kanban/tests/test_storage_io.py:269`, and each test creates its own temp board. |
| Descriptive names | STRONG | Test names are AC-specific throughout `serve/kanban/tests/test_storage_io.py:94-319`. |

#### Data Safety
- No issues found in the refined-AC scope. Cleanup is present at `serve/kanban/src/owlbear_kanban/storage_io.py:53-54`; per-task OCC locking is at `serve/kanban/src/owlbear_kanban/storage.py:331-342`; ID allocation locking is at `serve/kanban/src/owlbear_kanban/storage.py:418-423`; and the exclusive lock helper is at `serve/kanban/src/owlbear_kanban/engine.py:240-262`.

#### Implementation-Aware Gaps
- No separate critical implementation gaps found after checking related storage tests. The `FileNotFoundError` branch for `write_task_if_unchanged` is already covered in `serve/kanban/tests/test_storage_1050.py:782-794`.
- The blocker is assertion strength in this task’s `TestFromAC_*` cases, not missing implementation behavior.

#### Necessity Check
- Not applicable. No new dependency, integration, tool, or external capability was added.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes — the second pass re-verified against the refined AC and supplemented coverage with related storage tests. |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_storage_io.py:1-5` still advertises an all-failing RED suite even though the current snapshot is GREEN.
- No independent evidence of weakened `TestFromAC_*` assertions was found in the current snapshot, but historical immutability could not be proven without a diff-capable tool.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C1 | `serve/kanban/src/owlbear_kanban/storage_io.py:31-49` implements sibling tmp creation, file fsync, replace, and POSIX dir fsync. Current tests are too lax to certify that contract against mutation. | `test_ac_c1_*` | PASS |
| AC-C2 | Cleanup and unchanged-target behavior before the commit point are exercised at `serve/kanban/tests/test_storage_io.py:142-170`; cleanup logic is in `serve/kanban/src/owlbear_kanban/storage_io.py:53-54`. | `test_ac_c2_*` | PASS |
| AC-C3 | Hidden/temp filtering is in `serve/kanban/src/owlbear_kanban/storage.py:357-362`; the task test passes at `serve/kanban/tests/test_storage_io.py:172-183`. | `test_ac_c3_list_task_files_excludes_tmp` | PASS |
| AC-C4 | `serve/kanban/src/owlbear_kanban/storage.py:418-423` holds `.next_id.lock` across load/increment/save, and `serve/kanban/src/owlbear_kanban/engine.py:240-262` provides the exclusive file lock; the 50-thread distinct-ID test passes at `serve/kanban/tests/test_storage_io.py:194-218`. | `test_ac_c4_50_concurrent_threads_yield_distinct_ids` | PASS |
| AC-C4a | `serve/kanban/src/owlbear_kanban/storage.py:331-342` locks `tasks/.<id>.lock` and raises `ERR_STALE`; the race and survivor tests pass at `serve/kanban/tests/test_storage_io.py:220-291`. | `test_ac_c4a_*` | PASS |
| AC-C4b | `serve/kanban/src/owlbear_kanban/storage.py:331` uses `tasks/.<id>.lock`; `serve/kanban/src/owlbear_kanban/storage.py:357-375` excludes hidden/temp files from task/archive listings; the task tests pass at `serve/kanban/tests/test_storage_io.py:293-317`, but only the exclusion half is directly protected by assertions. | `test_ac_c4b_*` | PASS |
| AC-C51 | `serve/kanban/tests/test_storage_io.py:319-340` asserts burned-ID behavior under the refined AC, and `serve/kanban/src/owlbear_kanban/storage.py:418-423` shows the increment/save order. | `test_ac_c51_crash_between_save_config_and_write_task` | PASS |

### Deductions
- 0.08 AC-C1 assertions are too weak to guard sibling placement and parent-dir-fsync semantics.
- 0.04 AC-C4b does not directly protect the `tasks/.<id>.lock` location clause.

### Confidence: 0.88
### Verdict: FAIL
### Action
Reject to `todo`. No implementation change is required by the current evidence. The next cycle should strengthen `TestFromAC_*` assertions for AC-C1 and AC-C4b so incorrect implementations would fail instead of false-greening.
[[2026-04-21]]
## Test-Writer Notes
- Retry cycle: reviewer FAILed for weak assertions on AC-C1 and AC-C4b (confidence 0.88 → reject to `todo`)
- Test file: `serve/kanban/tests/test_storage_io.py`
- Classes: `TestFromAC_AtomicWrite`, `TestFromAC_IDAllocation`
- Total: 13 tests — all GREEN (implementation present from prior cycle)

**Changes made (assertion strengthening):**

| Change | Target | What was added |
|--------|--------|----------------|
| Modified | `test_ac_c1_writes_via_tmp_sibling` | Captures full `Path(src)` instead of `.name`; asserts `tmp_used.parent == target.parent` (sibling placement) |
| Modified | `test_ac_c1_posix_fsyncs_file_and_dir` | Adds `os.open` spy tracking `parent_dir`-matching fds; asserts `any(fd in dir_fds for fd in fsync_calls)` — proves second fsync is specifically the parent-dir fd |
| Added | `test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path` | Calls `write_task_if_unchanged`; asserts `tasks/.1001.lock` exists afterward — directly verifies the location clause in AC-C4b |

**Mutation resistance now provided:**
- AC-C1 sibling: moving tmp to a different directory would fail the `parent == target.parent` assertion
- AC-C1 fsync order: fsyncing file fd twice (skipping dir fd) would fail `any(fd in dir_fds for fd in fsync_calls)`
- AC-C4b lock path: using a different lock location would fail the `expected_lock.exists()` assertion

**AC coverage:**
| AC | Test(s) | Status |
|----|---------|--------|
| AC-C1 | `test_ac_c1_*` (3) | COVERED (strengthened) |
| AC-C2 | `test_ac_c2_*` (2) | COVERED |
| AC-C3 | `test_ac_c3_list_task_files_excludes_tmp` | COVERED |
| AC-C4 | `test_ac_c4_50_concurrent_threads_yield_distinct_ids` | COVERED |
| AC-C4a | `test_ac_c4a_*` (2) | COVERED |
| AC-C4b | `test_ac_c4b_*` (3 — 2 existing + 1 new) | COVERED (lock-path guard added) |
| AC-C51 | `test_ac_c51_crash_between_save_config_and_write_task` | COVERED |

- ruff: clean
- commit: 8d51932c
[[2026-04-21]]
## Builder Notes
- Implementation: No code changes in this cycle; existing behavior in serve/kanban/src/owlbear_kanban/storage_io.py and serve/kanban/src/owlbear_kanban/storage.py satisfies the refined AC.
- RED verification context: `TestFromAC_*` tests are already GREEN in this retry cycle (implementation landed previously); quality-runner evidence captured before advancement.
- Tests: 13 TestFromAC passed in serve/kanban/tests/test_storage_io.py; 0 TestBuilderDiscovered added.
- Regression check: 73 passed, 0 failed, 0 skipped across serve/kanban/tests/test_storage_io.py, serve/kanban/tests/test_storage.py, serve/kanban/tests/test_storage_1050.py.
- Coverage: owlbear_kanban.storage_io 100%; owlbear_kanban.storage 96%.
- Ruff: clean for serve/kanban/src/owlbear_kanban/storage_io.py, serve/kanban/src/owlbear_kanban/storage.py, and serve/kanban/tests/test_storage_io.py.
- Evidence summary: quality-runner scoped verification returned failed_test_names: [] and lint_clean: true.
- Fixes applied: none.
- Post-task reflection:
  - Problem faced: Task remained in-progress for formal builder advancement despite already-green implementation.
  - Workaround applied: Performed fresh quality-runner verification with module-level storage tests to produce canonical, current evidence.
  - Pattern discovered: Retroactive formalization passes should capture both task-scoped and adjacent module-level evidence to avoid stale gate decisions.
  - Time sink: Evidence refresh only; no code/debug loop.
  - Quality gap: None blocking this task after strengthened AC assertions and module-level coverage run.
[[2026-04-22]]
## Review Evidence
### Test Results
- Quality-Runner scoped run on serve/kanban/tests/test_storage_io.py: 13 passed, 0 failed, 0 skipped.
- Supplemental storage-module run on serve/kanban/tests/test_storage_io.py, serve/kanban/tests/test_storage.py, and serve/kanban/tests/test_storage_1050.py: 73 passed, 0 failed, 0 skipped.

### Lint
- Ruff clean for serve/kanban/src/owlbear_kanban/storage_io.py, serve/kanban/src/owlbear_kanban/storage.py, and serve/kanban/tests/test_storage_io.py.

### Coverage
- owlbear_kanban.storage_io: 100 percent.
- owlbear_kanban.storage: 75 percent in task-only scope; 96 percent when related storage tests are included.
- Coverage is not the blocker for this review. The supplemental run clears the touched-module gate.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C1 | test_ac_c1_writes_via_tmp_sibling; test_ac_c1_posix_fsyncs_file_and_dir; test_ac_c1_final_content_is_correct | No. serve/kanban/tests/test_storage_io.py:128-142 only proves at least two fsync calls and that one of them hit a parent-dir fd. A bad implementation could fsync the parent dir twice, never fsync the temp file fd, or fsync in the wrong order around replace and still pass. | LAX |
| AC-C2 | test_ac_c2_cleans_up_tmp_on_replace_failure; test_ac_c2_target_unaffected_on_fsync_failure | Yes. serve/kanban/tests/test_storage_io.py:153-187 covers replace failure and pre-replace fsync failure with cleanup and unchanged-target assertions, matching the refined commit-point contract. | COVERED |
| AC-C3 | test_ac_c3_list_task_files_excludes_tmp | Yes. serve/kanban/tests/test_storage_io.py:189-200 rejects .tmp-* entries. | COVERED |
| AC-C4 | test_ac_c4_50_concurrent_threads_yield_distinct_ids | No. serve/kanban/tests/test_storage_io.py:211-235 proves uniqueness under 50 threads, but it does not prove that serve/kanban/src/owlbear_kanban/storage.py:418-423 held .next_id.lock across read, increment, and save. A same-process-only lock would still pass. | LAX |
| AC-C4a | test_ac_c4a_cas_20_threads_one_success_19_stale; test_ac_c4a_survivor_write_intact | Yes. serve/kanban/tests/test_storage_io.py:237-308 enforces exact stale/success counts and verifies the survivor write. | COVERED |
| AC-C4b | test_ac_c4b_lock_files_not_in_list_task_files; test_ac_c4b_lock_files_not_in_list_archive_files; test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path | Yes for the refined AC. serve/kanban/tests/test_storage_io.py:310-351 now guards both list exclusion and the tasks/.<id>.lock location used at serve/kanban/src/owlbear_kanban/storage.py:331. | COVERED |
| AC-C51 | test_ac_c51_crash_between_save_config_and_write_task | Yes for the refined helper-level AC. serve/kanban/tests/test_storage_io.py:356-377 asserts next allocation = original_next_id + 1, config next_id = original_next_id + 2, and no burned task file. | COVERED |

#### Security Review
- No security issues found in scope. The reviewed code paths are local filesystem writes and file locks only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_AtomicWrite | Current snapshot strengthens the earlier weak area with sibling-path and dir-fsync assertions at serve/kanban/tests/test_storage_io.py:109-142. No skip/xfail markers observed. | PRESERVED (current snapshot) |
| TestFromAC_IDAllocation | Current snapshot strengthens AC-C4b with a direct per-task lock-path assertion at serve/kanban/tests/test_storage_io.py:336-351. No skip/xfail markers observed. | PRESERVED (current snapshot) |
- Historical immutability against the original RED commit was not independently re-verified with the available tool set.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most assertions are exact, including exact stale counts, exact success counts, exact lock-path existence, and exact burned-ID state. |
| Negative and error-path coverage | ADEQUATE | Replace failure, pre-replace fsync failure, and stale CAS paths are all exercised in serve/kanban/tests/test_storage_io.py:153-308. |
| Manual mutation reasoning | WEAK | AC-C1 still passes if the code fsyncs the parent dir twice and never fsyncs the temp file fd; AC-C4 still passes if uniqueness comes from some other serialization strategy instead of .next_id.lock. |
| Test independence | STRONG | Each case uses its own tmp_path board and local thread collectors. |
| Descriptive names | STRONG | Test names map directly to the refined AC lines. |

#### Data Safety
- Brief/task drift remains unresolved around the real create path. Brief C §1.4 says engine.py should consume storage as the boundary, and Brief C §3.3 / AC-C51 describes crash safety for create_task after save_config but before write_task. The current production create path still imports config_loader and task_io directly at serve/kanban/src/owlbear_kanban/engine.py:38 and :47, then writes the task before save_config at serve/kanban/src/owlbear_kanban/engine.py:662-696. The task suite only exercises allocate_next_id directly. That means the current tests can green-light helper behavior while the real consumer path still permits duplicate-ID-on-crash behavior.

#### Implementation-Aware Gaps
- No task-scoped test proves that atomic_write fsyncs the temp file fd before replace. serve/kanban/src/owlbear_kanban/storage_io.py:37-49 implements it, but the current AC-C1 assertions do not kill the wrong-order or missing-file-fsync mutations.
- No task-scoped test proves that allocate_next_id specifically uses .next_id.lock at serve/kanban/src/owlbear_kanban/storage.py:418-423.
- No task-scoped test exercises KanbanEngine.create_task crash behavior, even though paper-c.md:100 and :747 describe engine-boundary and create-task crash semantics.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability is involved.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes. The retries changed the review basis from original AC to refined AC and then strengthened test assertions for AC-C1 and AC-C4b. |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- serve/kanban/tests/test_storage_io.py:1-5 still describes the file as an all-failing RED suite even though the current snapshot is green.
- .gitignore:108 and seed/.gitignore:68 still only ignore .owlbear/kanban/.next_id.lock. That is outside the refined AC-C4b scope because architect split gitignore work to follow-up task #1096.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C1 | serve/kanban/src/owlbear_kanban/storage_io.py:16-53 implements the refined sequence, but the TestFromAC assertions do not fully certify file-fsync and ordering semantics. | PASS with test-quality risk |
| AC-C2 | Refined commit-point behavior is exercised by the replace-failure and pre-replace-fsync-failure tests at serve/kanban/tests/test_storage_io.py:153-187. | PASS |
| AC-C3 | list_task_files excludes hidden temp files at serve/kanban/src/owlbear_kanban/storage.py:346-356 and the task test passes. | PASS |
| AC-C4 | allocate_next_id uses .next_id.lock at serve/kanban/src/owlbear_kanban/storage.py:418-423 and the 50-thread uniqueness test passes, but the lock-path contract is not directly protected by assertions. | PASS with test-quality risk |
| AC-C4a | write_task_if_unchanged locks tasks/.<id>.lock at serve/kanban/src/owlbear_kanban/storage.py:331 and the race tests pass. | PASS |
| AC-C4b | The refined list-exclusion and per-task lock-path clauses are both exercised by serve/kanban/tests/test_storage_io.py:310-351. | PASS |
| AC-C51 | The refined helper-level burned-ID behavior is covered by serve/kanban/tests/test_storage_io.py:356-377. | PASS |

### Deductions
- 0.10 AC-C1 still allows false-green mutations around temp-file fsync and ordering.
- 0.08 AC-C4 still allows false-green mutations around the .next_id.lock contract.
- 0.10 Brief/task drift around AC-C51 leaves the real engine create_task crash path outside this task’s protection.

### Confidence: 0.72
### Verdict: FAIL
### Action
Reject to backlog. This is the third review failure on #1046, so the loop-breaker route applies. Architect and test-writer need to realign the task with the paper-c consumer-path contract and strengthen the remaining AC-C1 and AC-C4 assertions before another builder pass.
[[2026-04-22]]
## Architecture Review (Cycle 3 — Loop-Breaker Resolution)

### Previous Cycle Summary
3 review cycles: 0.37, 0.88, 0.72. Implementation correct, all 13 tests pass. Loop caused by test assertion quality gaps, not AC or implementation defects.

### Loop-Breaker Analysis
Reviewer deductions stem from three issues:
1. AC-C1 (0.10): Tests don't verify fsync ordering (file-fd fsync, replace, dir-fd fsync). Count/set-membership assertions pass wrong implementations.
2. AC-C4 (0.08): Tests don't verify .next_id.lock file is used by allocate_next_id specifically.
3. AC-C51 (0.10): Engine create_task crash path not tested. Out of this task's scope (storage helpers only). Confirmed no existing task owns this AC (#1053, #1062, #1097 all lack it). Follow-up #1101 created.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-C1 | IMPRECISE — ordering stated but not enforceable. Test-writer interpreted as count/membership checks. | Refined: explicit ordering verification requirement |
| AC-C2 | PASS — commit-point semantics clear | None |
| AC-C3 | PASS — straightforward filter | None |
| AC-C4 | IMPRECISE — .next_id.lock mentioned but no verification clause | Refined: added lock-file existence clause |
| AC-C4a | PASS — exact counts, survivor check | None |
| AC-C4b | PASS — strengthened in cycle 2 with lock-path test | None |
| AC-C51 | SCOPE MISMATCH — original said create_task (engine scope). Cycle 1 refined to allocate_next_id (correct for storage layer). | Clarified: explicit scope boundary. Follow-up #1101. |

### Refined AC (cycle 3 — authoritative, supersedes all prior AC)

- [ ] AC-C1: atomic_write(target, content) writes to .tmp-* sibling, fsyncs file fd, then os.replace to target, then fsyncs parent dir fd on POSIX. Tests must verify operation ordering: a shared sequence spy must prove file-fd fsync precedes replace which precedes dir-fd fsync. Count-only or set-membership-only assertions are insufficient.
- [ ] AC-C2: .tmp-* cleaned up on any exception. Target unaffected when exception occurs before os.replace (the commit point). Simulated: os.replace failure, pre-replace fsync failure.
- [ ] AC-C3: list_task_files filters out .tmp-* files.
- [ ] AC-C4: allocate_next_id holds .next_id.lock during read+increment+save. (a) 50 threads x 1 allocation yields 50 distinct IDs. (b) After first allocation, .next_id.lock file exists at kanban_dir/.next_id.lock.
- [ ] AC-C4a: write_task_if_unchanged CAS test: 20 threads racing yields exactly 1 success, 19 ERR_STALE; survivor write intact.
- [ ] AC-C4b: Lock files at tasks/.<id>.lock, never returned by list_task_files/list_archive_files.
- [ ] AC-C51: ID burn on crash: simulate crash after allocate_next_id bumps config but before write_task; next allocate_next_id returns original_next_id + 1; config ends at original_next_id + 2 (one ID burned, no task file for burned ID). Scope: allocate_next_id helper only; engine create_task crash safety tracked in #1101.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage I/O + ID allocation — cohesive primitives |
| Interface clarity | PASS (after refinement) | AC-C1 ordering, AC-C4 lock-existence now explicit |
| Dependency correctness | PASS | No deps; downstream tasks depend on this |
| Module layering | PASS | storage_io below storage; no upward imports |
| TDD compliance | PASS | RED task; implementation present from prior cycles |
| KISS/YAGNI | PASS | Minimal scope aligned with Brief C |
| Premise challenge | PASS | Atomic write and ID allocation are core storage primitives |
| Pattern consistency | PASS | flock, atomic_write, ConcurrencyError follow Brief C conventions |
| Security surface | PASS | No external input boundaries |
| Single domain | PASS | kanban storage domain only |

### Challenge Results
- Challenger: BLOCK (confidence: 0.33)
- 6 findings: AC-C51 scope ownership (critical), contract drift (critical), proposal-to-record mismatch (moderate), AC-C4 evidence insufficiency (moderate), evidence weighting (moderate), cross-task traceability (moderate)
- Architect response:
  - AC-C51 scope ownership: ACCEPTED. Confirmed #1053/#1062 lack AC-C51 engine crash AC. Created #1101 with explicit engine crash-safety AC.
  - Contract drift: OVERRIDDEN. Previous architect correctly refined AC-C51 from engine to helper scope. Test file is test_storage_io.py (storage layer). Engine-level crash safety now has explicit owner (#1101).
  - Proposal-to-record mismatch: ACCEPTED. Refinements written to body in this note.
  - AC-C4 evidence insufficiency: PARTIALLY ACCEPTED. Lock-file-exists proves mechanism is file-based (not threading.Lock). Behavioral guarantee from 50-thread uniqueness. Full critical-section proof unfalsifiable via unit test.
  - Evidence weighting: OVERRIDDEN. AC precision is the architect's scope. Refinements give the test-writer concrete direction for ordering verification.
  - Cross-task traceability: NOTED. #1055 (GREEN counterpart) undergoes its own architect review.

### Follow-up Tasks
- #1101: Engine create_task crash-safety test (AC-C51-engine). Created at research (create_task tool cannot set status to backlog). Should be moved to backlog. Tags needed: phase:storage, brief:c, scope:kanban. Parent: #1043. Depends on: #1062.
- Cleanup needed: #1098, #1099, #1100 are artifacts from create_task tool debugging. Should be deleted.

### Verdict: APPROVE (REFINE + APPROVE)
### Action: AC refined in cycle 3 above. Key changes: (1) AC-C1 requires ordering verification via shared sequence spy, (2) AC-C4 adds lock-file existence clause, (3) AC-C51 adds explicit scope boundary with follow-up #1101. Reviewer should evaluate against cycle 3 refined AC only.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle (cycle 3): reviewer FAILed for weak assertions on AC-C1 and AC-C4 (confidence 0.72); architect refined AC with ordering requirement and lock-file existence clause.
- Test file: `serve/kanban/tests/test_storage_io.py`
- Classes: `TestFromAC_AtomicWrite`, `TestFromAC_IDAllocation`
- Changes made (assertion strengthening):

| Change | Target | What was added |
|--------|--------|----------------|
| Added | `test_ac_c1_fsyncs_in_correct_order` | Sequence spy tracking `spy_open`/`spy_fsync`/`spy_replace`; asserts `sequence == ["fsync_file", "replace", "fsync_dir"]` — wrong ordering or wrong fd type fails |
| Added | `test_ac_c4_next_id_lock_file_exists_after_allocation` | Asserts `.next_id.lock` exists at `kanban_dir/.next_id.lock` after `allocate_next_id` — a `threading.Lock` or different path fails |

- Total: 15 tests (13 existing preserved + 2 new)
- ruff: clean
- commit: f992689d
- All 15 pass (implementation already correct from prior cycle)

**AC coverage (cycle 3 refined AC):**
| AC | Test(s) | Status |
|----|---------|--------|
| AC-C1 (ordering) | `test_ac_c1_writes_via_tmp_sibling`, `test_ac_c1_posix_fsyncs_file_and_dir`, `test_ac_c1_final_content_is_correct`, `test_ac_c1_fsyncs_in_correct_order` (NEW) | COVERED with ordering guard |
| AC-C2 | `test_ac_c2_cleans_up_tmp_on_replace_failure`, `test_ac_c2_target_unaffected_on_fsync_failure` | COVERED |
| AC-C3 | `test_ac_c3_list_task_files_excludes_tmp` | COVERED |
| AC-C4 (lock-file existence) | `test_ac_c4_50_concurrent_threads_yield_distinct_ids`, `test_ac_c4_next_id_lock_file_exists_after_allocation` (NEW) | COVERED with lock-path guard |
| AC-C4a | `test_ac_c4a_cas_20_threads_one_success_19_stale`, `test_ac_c4a_survivor_write_intact` | COVERED |
| AC-C4b | `test_ac_c4b_lock_files_not_in_list_task_files`, `test_ac_c4b_lock_files_not_in_list_archive_files`, `test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path` | COVERED |
| AC-C51 | `test_ac_c51_crash_between_save_config_and_write_task` | COVERED |
[[2026-04-22]]
## Builder Notes
- Implementation: no code changes in this cycle (existing implementation remains in `serve/kanban/src/owlbear_kanban/storage_io.py` and `serve/kanban/src/owlbear_kanban/storage.py`).
- Tests: 15 `TestFromAC_*` passed in scoped verification (`serve/kanban/tests/test_storage_io.py`); supplemental storage-module run: 78 passed, 0 failed, 0 skipped across `serve/kanban/tests/test_storage_io.py`, `serve/kanban/tests/test_storage.py`, `serve/kanban/tests/test_storage_1050.py`.
- Coverage: `owlbear_kanban.storage_io` 100%; `owlbear_kanban.storage` 75% in task-only scope and 96% with related storage tests (gate-clearing touched-module evidence).
- Ruff: clean for `serve/kanban/src/owlbear_kanban/storage_io.py`, `serve/kanban/src/owlbear_kanban/storage.py`, and `serve/kanban/tests/test_storage_io.py`.
- Evidence summary: quality-runner scoped and supplemental runs both returned `failed: []`, pytest exit code 0, and ruff exit code 0.
- Fixes applied: none.
- Post-task reflection:
  - Problem faced: this was a formalization cycle on already-correct code, so evidence freshness (not implementation) was the key risk.
  - Workaround applied: ran both task-scoped and supplemental storage-module quality-runner passes to avoid false gating from narrow-scope coverage.
  - Pattern discovered: dual evidence (scoped + module-level) is the most reliable closeout pattern for retroactive GREEN tasks.
  - Time sink: repeated re-verification overhead due to prior review-loop context.
  - Quality gap: none blocking after cycle-3 assertion-strengthening and current verification.
[[2026-04-22]]
## Review Evidence
### Test Results
- Quality-Runner scoped run: 15 passed, 0 failed, 0 skipped for serve/kanban/tests/test_storage_io.py.
- Supplemental storage-module run: 78 passed, 0 failed, 0 skipped for serve/kanban/tests/test_storage_io.py, serve/kanban/tests/test_storage.py, and serve/kanban/tests/test_storage_1050.py.

### Lint
- Clean for serve/kanban/src/owlbear_kanban/storage_io.py, serve/kanban/src/owlbear_kanban/storage.py, and serve/kanban/tests/test_storage_io.py.

### Coverage
- owlbear_kanban.storage_io: 100 percent.
- owlbear_kanban.storage: 75 percent in task-only scope; 96 percent when related storage tests are included.
- Coverage clears the touched-module gate when the related storage tests are included.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C1 | test_ac_c1_writes_via_tmp_sibling; test_ac_c1_posix_fsyncs_file_and_dir; test_ac_c1_final_content_is_correct; test_ac_c1_fsyncs_in_correct_order | Partially. The new ordering and sibling assertions are strong on POSIX, but the AC is explicitly POSIX-scoped while the dir-fsync assertions are unconditional at serve/kanban/tests/test_storage_io.py:116-186. Since atomic_write only performs the parent-dir fsync behind serve/kanban/src/owlbear_kanban/storage_io.py:46-49, these tests false-fail on supported Windows setups. | LAX |
| AC-C2 | test_ac_c2_cleans_up_tmp_on_replace_failure; test_ac_c2_target_unaffected_on_fsync_failure | Yes. Pre-commit exception cleanup and unchanged-target behavior are covered in serve/kanban/tests/test_storage_io.py. | COVERED |
| AC-C3 | test_ac_c3_list_task_files_excludes_tmp | Yes. Hidden temp files are rejected by list_task_files and by the task test. | COVERED |
| AC-C4 | test_ac_c4_50_concurrent_threads_yield_distinct_ids; test_ac_c4_next_id_lock_file_exists_after_allocation | Yes for the cycle-3 refined AC. The tests enforce 50 unique IDs and lock-file existence at kanban_dir/.next_id.lock, matching serve/kanban/src/owlbear_kanban/storage.py:418-427. | COVERED |
| AC-C4a | test_ac_c4a_cas_20_threads_one_success_19_stale; test_ac_c4a_survivor_write_intact | Yes. Exact success and stale counts plus readable survivor state are covered in serve/kanban/tests/test_storage_io.py. | COVERED |
| AC-C4b | test_ac_c4b_lock_files_not_in_list_task_files; test_ac_c4b_lock_files_not_in_list_archive_files; test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path | Yes. List exclusion and tasks/.<id>.lock creation match serve/kanban/src/owlbear_kanban/storage.py:310-381. | COVERED |
| AC-C51 | test_ac_c51_crash_between_save_config_and_write_task | Yes for the refined helper-scope AC. The task test covers burn-one-ID behavior after config advance and before write_task. | COVERED |

#### Security Review
- No issues found in scope. The reviewed code paths are local filesystem writes and file locks only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_AtomicWrite | Current snapshot strengthens AC-C1 with sibling-path and ordering assertions; no skip or xfail markers observed. | STRENGTHENED |
| TestFromAC_IDAllocation | Current snapshot strengthens AC-C4 with a direct .next_id.lock existence assertion; no skip or xfail markers observed. | STRENGTHENED |
- Historical immutability against the original RED commit was not independently re-verified with the available tool set, but no weakening is visible in the current snapshot.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | AC-C1 ordering and AC-C4 lock existence are now asserted exactly in serve/kanban/tests/test_storage_io.py. |
| Negative and error-path coverage | ADEQUATE | AC-C2 replace failure and pre-replace fsync failure, plus AC-C4a stale OCC behavior, are covered. |
| Manual mutation reasoning | ADEQUATE | Wrong fsync order and wrong lock path now fail on POSIX. |
| Test independence | STRONG | Each case creates its own temp board and uses local thread collectors. |
| Descriptive names | STRONG | Test names map directly to the refined AC lines. |
| Platform scoping | WEAK | AC-C1 is explicitly POSIX-scoped in the task body, but serve/kanban/tests/test_storage_io.py:116-186 asserts dir-fsync behavior unconditionally even though serve/kanban/src/owlbear_kanban/storage_io.py:46-49 gates that behavior by platform. The repo documents Windows support at setup/sharing-guide.md:64-68 and carries Windows code paths at serve/kanban/src/owlbear_kanban/engine.py:274-278. |

#### Data Safety
- No implementation-side data-safety issues found in the refined task scope.

#### Implementation-Aware Gaps
- No refined-scope implementation gap found. The blocker is test portability, not storage-helper behavior.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability is involved.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | Yes. The task history shows multiple evidence-refresh and assertion-strengthening passes rather than the same retry repeated. |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL
- serve/kanban/tests/test_storage_io.py:1-5 still describes the file as an all-failing RED suite even though the current snapshot is GREEN.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C1 | The refined AC is POSIX-scoped, but the current tests encode dir-fsync behavior unconditionally at serve/kanban/tests/test_storage_io.py:116-186 while the implementation only performs it behind serve/kanban/src/owlbear_kanban/storage_io.py:46-49. That makes the task's AC-C1 test artifact invalid on supported Windows environments. | FAIL |
| AC-C2 | Pre-commit cleanup and unchanged-target behavior are covered by the two AC-C2 tests and match the refined commit-point semantics. | PASS |
| AC-C3 | list_task_files excludes .tmp files and the task test passes. | PASS |
| AC-C4 | allocate_next_id uses .next_id.lock and the task tests now cover both uniqueness and lock-file existence. | PASS |
| AC-C4a | write_task_if_unchanged enforces one winner, stale losers, and intact survivor state. | PASS |
| AC-C4b | Per-task lock-path creation and lock-file exclusion from listings are both covered. | PASS |
| AC-C51 | The helper-scope burned-ID contract is covered by the task test; engine-level crash safety is tracked separately in #1101. | PASS |

### Deductions
- 0.12 AC-C1 tests are platform-mis-scoped and false-fail on supported Windows setups.

### Confidence: 0.88
### Verdict: FAIL
### Action
Reject to backlog. This is the fourth review cycle on #1046, so the loop-breaker route applies. No implementation change is required by current evidence. The next cycle should fix the AC-C1 tests so POSIX-only dir-fsync assertions are conditional on platforms that expose that behavior, then rerun task-scoped quality checks.
[[2026-04-22]]
## Architecture Review (Cycle 4 — Loop-Breaker Resolution)

### Previous Cycle Summary
4 review cycles: 0.37, 0.88, 0.72, 0.88. Implementation correct across all cycles. All 15 tests pass. Cycle 4 reviewer's sole deduction (0.12): `test_ac_c1_posix_fsyncs_file_and_dir` and `test_ac_c1_fsyncs_in_correct_order` assert dir-fsync behavior unconditionally, but `storage_io.py:46` gates it with `hasattr(os, "O_DIRECTORY")`.

### Loop-Breaker Analysis
The remaining issue is test platform-scoping, not AC precision or implementation correctness. Two tests encode POSIX-specific assertions without platform guards. The fix is surgical: skip or condition the dir-fsync assertions on platforms without `O_DIRECTORY`.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-C1 | IMPRECISE on platform scope — cycle 3 said "on POSIX" but didn't require test guards. Challenger correctly noted: (a) "POSIX" should be `hasattr(os, "O_DIRECTORY")` (feature detection, not platform identity), (b) full-ordering test skip would lose file-fsync-before-replace verification cross-platform. | Refined: split platform-conditional from platform-unconditional assertions |
| AC-C2 | PASS | None |
| AC-C3 | PASS | None |
| AC-C4 | PASS | None |
| AC-C4a | PASS | None |
| AC-C4b | PASS | None |
| AC-C51 | PASS | None |

### Refined AC (cycle 4 — authoritative, supersedes all prior AC)

- [ ] AC-C1: `atomic_write(target, content)` writes to `.tmp-*` sibling, fsyncs file fd, `os.replace` to target. When `hasattr(os, "O_DIRECTORY")`, fsyncs parent dir fd after replace. Tests must verify: (a) file-fd fsync precedes replace — unconditional, all platforms; (b) dir-fd fsync follows replace — conditional on `hasattr(os, "O_DIRECTORY")`. Concretely: ordering spy must assert `["fsync_file", "replace"]` always, and `["fsync_file", "replace", "fsync_dir"]` only when `O_DIRECTORY` available. The dir-fsync count/membership test (`test_ac_c1_posix_fsyncs_file_and_dir`) must be guarded with `pytest.mark.skipif(not hasattr(os, "O_DIRECTORY"), reason="dir-fsync requires O_DIRECTORY")`.
- [ ] AC-C2: `.tmp-*` cleaned up on any exception. Target unaffected when exception occurs before `os.replace` (the commit point). Simulated: `os.replace` failure, pre-replace `fsync` failure.
- [ ] AC-C3: `list_task_files` filters out `.tmp-*` files.
- [ ] AC-C4: `allocate_next_id` holds `.next_id.lock` during read+increment+save. (a) 50 threads × 1 allocation → 50 distinct IDs. (b) After first allocation, `.next_id.lock` file exists at `kanban_dir/.next_id.lock`.
- [ ] AC-C4a: `write_task_if_unchanged` CAS test: 20 threads racing → exactly 1 success, 19 `ERR_STALE`; survivor write intact.
- [ ] AC-C4b: Lock files at `tasks/.<id>.lock`, never returned by `list_task_files`/`list_archive_files`.
- [ ] AC-C51: ID burn on crash: simulate crash after `allocate_next_id` bumps config but before `write_task`; next `allocate_next_id` returns `original_next_id + 1`; config ends at `original_next_id + 2` (one ID burned, no task file for burned ID). Scope: `allocate_next_id` helper only; engine `create_task` crash safety tracked in #1101.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage I/O + ID allocation — cohesive primitives |
| Interface clarity | PASS (after refinement) | AC-C1 platform scoping now explicit with feature detection |
| Dependency correctness | PASS | No deps; downstream tasks depend on this |
| Module layering | PASS | storage_io below storage; no upward imports |
| TDD compliance | PASS | RED+GREEN complete from prior cycles |
| KISS/YAGNI | PASS | Minimal scope aligned with Brief C |
| Premise challenge | PASS | Core storage primitives |
| Pattern consistency | PASS | flock, atomic_write, ConcurrencyError follow Brief C conventions |
| Security surface | PASS | No external input boundaries |
| Single domain | PASS | kanban storage domain only |

### Challenge Results
- Challenger: RECONSIDER (confidence: 0.63)
- 4 findings: contract drift (moderate), gate evidence gap (moderate), unsupported stability claim (minor), terminology mismatch (minor)
- Architect response:
  - Contract drift: ACCEPTED. Refined AC-C1 to split unconditional (file-fsync before replace) from conditional (dir-fsync after replace) with explicit test guidance. Ordering test should assert `["fsync_file", "replace"]` on all platforms, full `["fsync_file", "replace", "fsync_dir"]` only when `O_DIRECTORY` available.
  - Gate evidence gap: OVERRIDDEN. Pipeline flow: architect refines AC → task advances to `todo` → test-writer implements → builder verifies → reviewer checks fresh evidence. This is normal pipeline operation, not a gate bypass.
  - Unsupported stability claim: NOTED. Implementation is correct. Tests would only false-fail on Windows, not produce incorrect behavior.
  - Terminology mismatch: ACCEPTED. AC now uses `hasattr(os, "O_DIRECTORY")` (feature detection) instead of "POSIX".

### Verdict: APPROVE (REFINE + APPROVE)
### Action: AC-C1 refined to require platform-conditional test assertions using feature detection. Reviewer should evaluate against cycle 4 refined AC only.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle (cycle 4): reviewer FAILed for platform-mis-scoped AC-C1 assertions (confidence 0.88); architect refined AC-C1 with explicit `hasattr(os, "O_DIRECTORY")` feature-detection requirement.
- Test file: `serve/kanban/tests/test_storage_io.py`
- Classes: `TestFromAC_AtomicWrite`, `TestFromAC_IDAllocation`
- Total: 15 tests — all GREEN (implementation already correct from prior cycle)

**Changes made (platform scoping):**

| Change | Target | What was changed |
|--------|--------|-----------------|
| Modified | `test_ac_c1_posix_fsyncs_file_and_dir` | Added `@pytest.mark.skipif(not hasattr(os, "O_DIRECTORY"), reason="dir-fsync requires O_DIRECTORY (POSIX only)")` — test skips on platforms without `O_DIRECTORY` |
| Modified | `test_ac_c1_fsyncs_in_correct_order` | Replaced unconditional `assert sequence == ["fsync_file", "replace", "fsync_dir"]` with conditional: asserts `["fsync_file", "replace", "fsync_dir"]` when `O_DIRECTORY` available, `["fsync_file", "replace"]` otherwise — cross-platform correct |

**Why these changes and not new tests:** Architect cycle 4 AC refinement explicitly directed these modifications. The reviewer's sole deduction (0.12) was platform-mis-scoped assertions on the two AC-C1 tests — a test quality issue with specific architect guidance, not missing test coverage.

**AC coverage (cycle 4 refined AC):**
| AC | Test(s) | Status |
|----|---------|--------|
| AC-C1 (ordering, platform-conditional) | `test_ac_c1_writes_via_tmp_sibling`, `test_ac_c1_posix_fsyncs_file_and_dir` (skipif guarded), `test_ac_c1_final_content_is_correct`, `test_ac_c1_fsyncs_in_correct_order` (conditional) | COVERED with platform guards |
| AC-C2 | `test_ac_c2_cleans_up_tmp_on_replace_failure`, `test_ac_c2_target_unaffected_on_fsync_failure` | COVERED |
| AC-C3 | `test_ac_c3_list_task_files_excludes_tmp` | COVERED |
| AC-C4 | `test_ac_c4_50_concurrent_threads_yield_distinct_ids`, `test_ac_c4_next_id_lock_file_exists_after_allocation` | COVERED |
| AC-C4a | `test_ac_c4a_cas_20_threads_one_success_19_stale`, `test_ac_c4a_survivor_write_intact` | COVERED |
| AC-C4b | `test_ac_c4b_lock_files_not_in_list_task_files`, `test_ac_c4b_lock_files_not_in_list_archive_files`, `test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path` | COVERED |
| AC-C51 | `test_ac_c51_crash_between_save_config_and_write_task` | COVERED |

- ruff: clean
- pytest: 15 passed, 0 failed (macOS — `O_DIRECTORY` available, POSIX tests run)
- commit: 37bb8027
[[2026-04-22]]
## Builder Notes
- Implementation: no code changes in this cycle; existing implementation in serve/kanban/src/owlbear_kanban/storage_io.py and serve/kanban/src/owlbear_kanban/storage.py already satisfies the cycle-4 refined AC.
- Tests: 15 TestFromAC cases in serve/kanban/tests/test_storage_io.py remain GREEN; supplemental storage-module verification passed for serve/kanban/tests/test_storage_io.py, serve/kanban/tests/test_storage.py, and serve/kanban/tests/test_storage_1050.py.
- Verification results (quality-runner): 78 passed, 0 failed, 0 skipped; pytest exit 0.
- Coverage: owlbear_kanban.storage 96%; owlbear_kanban.storage_io 100%.
- Ruff: clean for serve/kanban/src/owlbear_kanban/storage_io.py, serve/kanban/src/owlbear_kanban/storage.py, and serve/kanban/tests/test_storage_io.py (ruff exit 0).
- Evidence summary: quality-runner report returned failed: [] and clean: true with no execution errors.
- Fixes applied: none required.
- Post-task reflection:
  - Problem faced: repeated review loops had left the task in in-progress despite implementation being stable.
  - Workaround applied: refreshed canonical evidence via quality-runner using scoped + related module paths.
  - Pattern discovered: retroactive GREEN closeout is reliable when both task scope and adjacent module paths are verified together.
  - Time sink: prior cycle context reconciliation, not code debugging.
  - Quality gap: none blocking after cycle-4 AC-C1 platform-scoping updates.
[[2026-04-22]]
## Review Evidence
### Test Results
- Independent quality-runner scoped run on `serve/kanban/tests/test_storage_io.py`: 15 passed, 0 failed, 0 skipped.
- Independent quality-runner supplemental storage-module run on `serve/kanban/tests/test_storage_io.py`, `serve/kanban/tests/test_storage.py`, and `serve/kanban/tests/test_storage_1050.py`: 78 passed, 0 failed, 0 skipped.

### Lint
- Ruff clean for `serve/kanban/src/owlbear_kanban/storage_io.py`, `serve/kanban/src/owlbear_kanban/storage.py`, and `serve/kanban/tests/test_storage_io.py`.

### Coverage
- Task-scoped: `owlbear_kanban.storage_io` 100%, `owlbear_kanban.storage` 75%.
- Supplemental related-storage run: `owlbear_kanban.storage` 96%.
- Coverage is not the blocker.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C1 | `atomic_write` sequence is implemented at `serve/kanban/src/owlbear_kanban/storage_io.py:16-52` and guarded by task tests at `serve/kanban/tests/test_storage_io.py:94-193`, including platform-conditional ordering. | PASS |
| AC-C2 | The implementation only cleans up temp files under `except Exception:` at `serve/kanban/src/owlbear_kanban/storage_io.py:52-54`, while the task AC says `.tmp-*` is cleaned up on any exception. The task suite only proves `OSError` paths at `serve/kanban/tests/test_storage_io.py:201-224`. A non-`Exception` failure after temp creation would leak `.tmp-*`. | FAIL |
| AC-C3 | Hidden/temp filtering is implemented by `list_task_files` at `serve/kanban/src/owlbear_kanban/storage.py:355-367` and exercised at `serve/kanban/tests/test_storage_io.py:231-242`. | PASS |
| AC-C4 | `allocate_next_id` holds `.next_id.lock` around load/increment/save at `serve/kanban/src/owlbear_kanban/storage.py:418-427`; the tests verify 50 distinct IDs and lock-file existence at `serve/kanban/tests/test_storage_io.py:253-289`. | PASS |
| AC-C4a | `write_task_if_unchanged` locks `tasks/.<id>.lock` and enforces `ERR_STALE` at `serve/kanban/src/owlbear_kanban/storage.py:310-347`; the race and survivor tests pass at `serve/kanban/tests/test_storage_io.py:293-364`. | PASS |
| AC-C4b | Per-task lock path and list exclusion are implemented at `serve/kanban/src/owlbear_kanban/storage.py:331-379` and exercised at `serve/kanban/tests/test_storage_io.py:366-410`. | PASS |
| AC-C51 | Burn-one-ID helper behavior is exercised at `serve/kanban/tests/test_storage_io.py:412-433`, matching `allocate_next_id` at `serve/kanban/src/owlbear_kanban/storage.py:418-427`. | PASS |

#### Security Review
- No security issues found in scope. Reviewed code is local filesystem write/lock logic only.

#### Test Integrity
- No weakened `TestFromAC_*` assertions observed in the current snapshot. The cycle-4 changes strengthen AC-C1 and AC-C4 coverage rather than relaxing them.

#### Test Quality
- STRONG/ADEQUATE overall after the cycle-4 refinements, except for the AC-C2 gap above: the suite does not exercise the non-`Exception` branch implied by the current AC wording.

#### Data Safety
- Blocking issue: `.tmp-*` cleanup does not currently cover all exception types promised by AC-C2 because the handler is `except Exception:` instead of a broader cleanup path.

#### Implementation-Aware Gaps
- The gap is narrow but real: no task-scoped test proves cleanup on a non-`Exception` failure path after temp creation.

#### Builder Process Quality
- CLEAN. The task body shows multiple retries with changed approach, not the same retry repeated.
- Loop-breaker routing still applies because this is now the fifth review cycle on #1046.

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_storage_io.py:1-5` still describes the file as an all-failing RED suite even though the current snapshot is green.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C1 | `serve/kanban/src/owlbear_kanban/storage_io.py:16-52`; `serve/kanban/tests/test_storage_io.py:94-193` | PASS |
| AC-C2 | `serve/kanban/src/owlbear_kanban/storage_io.py:52-54`; `serve/kanban/tests/test_storage_io.py:201-224` | FAIL |
| AC-C3 | `serve/kanban/src/owlbear_kanban/storage.py:355-367`; `serve/kanban/tests/test_storage_io.py:231-242` | PASS |
| AC-C4 | `serve/kanban/src/owlbear_kanban/storage.py:418-427`; `serve/kanban/tests/test_storage_io.py:253-289` | PASS |
| AC-C4a | `serve/kanban/src/owlbear_kanban/storage.py:310-347`; `serve/kanban/tests/test_storage_io.py:293-364` | PASS |
| AC-C4b | `serve/kanban/src/owlbear_kanban/storage.py:331-379`; `serve/kanban/tests/test_storage_io.py:366-410` | PASS |
| AC-C51 | `serve/kanban/tests/test_storage_io.py:412-433`; `serve/kanban/src/owlbear_kanban/storage.py:418-427` | PASS |

### Deductions
- 0.12 AC-C2 contract miss: cleanup is implemented only for `Exception`, but the authoritative AC still says cleanup happens on any exception; the task tests only cover `OSError`-style failures.

### Confidence: 0.88
### Verdict: FAIL
### Action
Reject to `backlog`.

This is the fifth review cycle, so the loop-breaker route applies. The next cycle should resolve the contract mismatch explicitly:
1. If AC-C2 truly means all exception types after temp creation, builder must broaden cleanup in `atomic_write` and test-writer must add a regression that proves the cleanup path.
2. If AC-C2 is intended to cover only normal `Exception`/`OSError` failure modes, architect must narrow the AC wording so the implementation and tests match the contract.
[[2026-04-22]]
## Architecture Review (Cycle 5 — Loop-Breaker Resolution)

### Previous Cycle Summary
5 review cycles: 0.37, 0.88, 0.72, 0.88, 0.88. Implementation correct, all 15 tests pass. Cycle 5 reviewer's sole deduction (0.12): AC-C2 says "any exception" but `storage_io.py:52` uses `except Exception:`, excluding `BaseException` subclasses (`KeyboardInterrupt`, `SystemExit`).

### Loop-Breaker Analysis
The reviewer's deduction is technically precise — `except Exception:` doesn't catch `BaseException` subclasses. But the brief's own evidence resolves this:

1. **Brief pseudocode (paper-c.md line 203)**: Explicitly uses `except Exception:`, not `except BaseException:`. The implementation follows the brief's reference code exactly.
2. **Brief crash model (paper-c.md §3.2 line 229)**: "A crash mid-write (between mkstemp and os.replace) leaves target untouched and a .tmp-XXXX file in the parent directory; list_task_files filters out .tmp-* patterns." — `BaseException` scenarios (KeyboardInterrupt, SystemExit) are process-termination events modeled as "crash mid-write," not as normal exception paths.
3. **Brief AC-C2 (paper-c.md line 664)**: "any exception path" is ordinary-language shorthand that drifts from the brief's own pseudocode. The intended contract scope is `Exception`-subclass failures, with crash-mid-write handled separately by the §3.2 tolerance model.

The resolution: align AC-C2 wording with the brief's pseudocode and crash model. This is a wording clarification, not a contract narrowing — the brief already defines two distinct layers.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-C1 | PASS — platform-conditional ordering verified | None |
| AC-C2 | BRIEF DRIFT — "any exception" in AC conflicts with brief's own `except Exception:` pseudocode. The brief models crash-mid-write (.tmp-* leftovers) separately in §3.2. | Refined: specify `Exception`-subclass scope; note crash-mid-write is §3.2 domain |
| AC-C3 | PASS | None |
| AC-C4 | PASS — lock-file existence verified | None |
| AC-C4a | PASS | None |
| AC-C4b | PASS | None |
| AC-C51 | PASS — helper scope with #1101 for engine | None |

### Refined AC (cycle 5 — authoritative, supersedes all prior AC)

- [ ] AC-C1: `atomic_write(target, content)` writes to `.tmp-*` sibling, fsyncs file fd, `os.replace` to target. When `hasattr(os, "O_DIRECTORY")`, fsyncs parent dir fd after replace. Tests must verify: (a) file-fd fsync precedes replace — unconditional, all platforms; (b) dir-fd fsync follows replace — conditional on `hasattr(os, "O_DIRECTORY")`. The dir-fsync count/membership test must be guarded with `pytest.mark.skipif(not hasattr(os, "O_DIRECTORY"), reason="dir-fsync requires O_DIRECTORY")`.
- [ ] AC-C2: `.tmp-*` cleaned up on any `Exception`-subclass failure (matching brief pseudocode §3.1 line 203). Target unaffected when exception occurs before `os.replace` (the commit point). Simulated: `os.replace` failure, pre-replace `fsync` failure. Note: `BaseException` scenarios (KeyboardInterrupt, process kill) are crash-mid-write events per brief §3.2 — `.tmp-*` leftovers are tolerated by `list_task_files` filtering (AC-C3).
- [ ] AC-C3: `list_task_files` filters out `.tmp-*` files.
- [ ] AC-C4: `allocate_next_id` holds `.next_id.lock` during read+increment+save. (a) 50 threads × 1 allocation → 50 distinct IDs. (b) After first allocation, `.next_id.lock` file exists at `kanban_dir/.next_id.lock`.
- [ ] AC-C4a: `write_task_if_unchanged` CAS test: 20 threads racing → exactly 1 success, 19 `ERR_STALE`; survivor write intact.
- [ ] AC-C4b: Lock files at `tasks/.<id>.lock`, never returned by `list_task_files`/`list_archive_files`.
- [ ] AC-C51: ID burn on crash: simulate crash after `allocate_next_id` bumps config but before `write_task`; next `allocate_next_id` returns `original_next_id + 1`; config ends at `original_next_id + 2` (one ID burned, no task file for burned ID). Scope: `allocate_next_id` helper only; engine `create_task` crash safety tracked in #1101.

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Storage I/O + ID allocation — cohesive primitives |
| Interface clarity | PASS (after refinement) | AC-C2 exception scope now matches brief pseudocode |
| Dependency correctness | PASS | No deps; downstream tasks depend on this |
| Module layering | PASS | storage_io below storage; no upward imports |
| TDD compliance | PASS | RED+GREEN complete from prior cycles |
| KISS/YAGNI | PASS | Minimal scope aligned with Brief C |
| Premise challenge | PASS | Core storage primitives |
| Pattern consistency | PASS | flock, atomic_write, ConcurrencyError follow Brief C |
| Security surface | PASS | No external input boundaries |
| Single domain | PASS | kanban storage domain only |

### Challenge Results
- Challenger: RECONSIDER (confidence: 0.66)
- 5 findings: record mismatch (moderate), brief-contract change framing (moderate), safety argument scope (moderate), docstring over-read (minor), anti-pattern claim (minor)
- Architect response:
  - Record mismatch: ACCEPTED. Refinement written to body in this note via standard REFINE+APPROVE flow.
  - Brief-contract change framing: OVERRIDDEN. The brief's own pseudocode (paper-c.md line 203) uses `except Exception:`. The brief's crash model (§3.2) separately handles process-termination leftovers. The AC refinement aligns with the brief's intended two-layer contract, not against it.
  - Safety argument scope: PARTIALLY ACCEPTED. All `atomic_write` callers (config, task, activity, migration, corruption) use the same cleanup-and-reraise pattern — the caller always receives the exception. A `.tmp-*` leftover from a `BaseException` is a crash-mid-write artifact per §3.2, handled by list filtering and normal cleanup on next startup. The safety argument extends beyond `list_task_files` to the brief's entire crash tolerance model.
  - Docstring over-read: ACCEPTED. Removed from reasoning; the brief pseudocode is the authoritative source.
  - Anti-pattern claim: PARTIALLY ACCEPTED. The stronger argument is architectural: `BaseException` is a process-termination signal, and the brief models this as "crash mid-write" (§3.2), not as an exception-handling path. The cleanup-and-reraise pattern under `except Exception:` is the intended scope per the brief's own reference implementation.

### Verdict: APPROVE (REFINE + APPROVE)
### Action: AC-C2 refined to specify `Exception`-subclass scope with brief §3.2 crash-model cross-reference. No code or test changes needed — implementation and tests already match the refined AC. Reviewer should evaluate against cycle 5 refined AC only.
[[2026-04-22]]
## Test-Writer Notes
- Retry cycle (cycle 5): reviewer FAILed (confidence 0.88) for AC-C2 contract mismatch — implementation used `except Exception:` but AC wording said "any exception". Architect cycle-5 review resolved by refining AC-C2 to specify `Exception`-subclass scope, cross-referencing brief §3.2 crash model for `BaseException` scenarios (process-termination events tolerated by list filtering, not cleanup).
- Test file: `serve/kanban/tests/test_storage_io.py`
- Classes: `TestFromAC_AtomicWrite`, `TestFromAC_IDAllocation`
- Total: 15 tests — all GREEN (implementation already correct from prior cycle)

**Why pass-through (no new tests):** Architect cycle-5 verdict explicitly states "No code or test changes needed — implementation and tests already match the refined AC." The reviewer's AC-C2 deduction was a wording gap, not a missing test or missing implementation path. Existing `test_ac_c2_cleans_up_tmp_on_replace_failure` and `test_ac_c2_target_unaffected_on_fsync_failure` cover the `Exception`-subclass cleanup contract as now defined.

**AC coverage (cycle 5 refined AC):**
| AC | Test(s) | Status |
|----|---------|--------|
| AC-C1 (ordering, platform-conditional) | `test_ac_c1_*` (4, incl. skipif guard) | COVERED |
| AC-C2 (Exception-subclass scope) | `test_ac_c2_cleans_up_tmp_on_replace_failure`, `test_ac_c2_target_unaffected_on_fsync_failure` | COVERED |
| AC-C3 | `test_ac_c3_list_task_files_excludes_tmp` | COVERED |
| AC-C4 (lock-file existence) | `test_ac_c4_50_concurrent_threads_yield_distinct_ids`, `test_ac_c4_next_id_lock_file_exists_after_allocation` | COVERED |
| AC-C4a | `test_ac_c4a_cas_20_threads_one_success_19_stale`, `test_ac_c4a_survivor_write_intact` | COVERED |
| AC-C4b | `test_ac_c4b_lock_files_not_in_list_task_files`, `test_ac_c4b_lock_files_not_in_list_archive_files`, `test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path` | COVERED |
| AC-C51 | `test_ac_c51_crash_between_save_config_and_write_task` | COVERED |

Pass-through to builder for reviewer re-evaluation against cycle-5 refined AC.
[[2026-04-22]]
## Builder Notes
- Implementation: no code changes in this cycle; existing behavior in serve/kanban/src/owlbear_kanban/storage_io.py and serve/kanban/src/owlbear_kanban/storage.py already satisfies the cycle-5 refined AC.
- Tests: scoped verification on serve/kanban/tests/test_storage_io.py passed 15/15 (0 failed, 0 skipped); supplemental storage-module verification on serve/kanban/tests/test_storage_io.py, serve/kanban/tests/test_storage.py, and serve/kanban/tests/test_storage_1050.py passed 78/78 (0 failed, 0 skipped).
- Coverage: owlbear_kanban.storage_io 100%; owlbear_kanban.storage 95% in supplemental run.
- Ruff: clean for serve/kanban/src/owlbear_kanban/storage_io.py, serve/kanban/src/owlbear_kanban/storage.py, and serve/kanban/tests/test_storage_io.py.
- Evidence summary: independent quality-runner pass reported failed tests: [] with pytest exit code 0 and ruff exit code 0.
- Fixes applied: none.
- Post-task reflection:
  - Problem faced: retroactive formalization task with many prior review cycles required fresh, canonical evidence rather than new implementation work.
  - Workaround applied: executed independent quality-runner scoped and supplemental storage-module verification in the same cycle.
  - Pattern discovered: dual evidence (task-scoped + adjacent module-level) reliably closes stale in-progress tasks without conflating unrelated suite issues.
  - Time sink: evidence refresh and prior-cycle context reconciliation.
  - Quality gap: none blocking for this task after cycle-5 AC refinement.
[[2026-04-22]]
## Review Evidence
### Test Results
- Quality-Runner scoped run: 15 passed, 0 failed, 0 skipped for `serve/kanban/tests/test_storage_io.py`.
- Quality-Runner supplemental storage run: 78 passed, 0 failed, 0 skipped for `serve/kanban/tests/test_storage_io.py`, `serve/kanban/tests/test_storage.py`, and `serve/kanban/tests/test_storage_1050.py`.

### Lint
- Clean for `serve/kanban/src/owlbear_kanban/storage_io.py`, `serve/kanban/src/owlbear_kanban/storage.py`, and `serve/kanban/tests/test_storage_io.py`.

### Coverage
- `owlbear_kanban.storage_io`: 100%.
- `owlbear_kanban.storage`: 74% in task-only scope and 95% when related storage tests are included.
- Supplemental coverage clears the touched-module gate for the storage helper surface exercised by adjacent storage suites.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C1 | `test_ac_c1_writes_via_tmp_sibling`, `test_ac_c1_posix_fsyncs_file_and_dir`, `test_ac_c1_final_content_is_correct`, `test_ac_c1_fsyncs_in_correct_order` | Yes. The sibling-path, conditional dir-fsync, final-content, and exact ordering assertions in `serve/kanban/tests/test_storage_io.py:94`, `:120`, `:150`, and `:157` would fail if `atomic_write` stopped using a sibling temp file, skipped file-fsync before replace, or skipped the conditional parent-dir fsync defined in `serve/kanban/src/owlbear_kanban/storage_io.py:16`, `:44`, and `:46`. | COVERED |
| AC-C2 | `test_ac_c2_cleans_up_tmp_on_replace_failure`, `test_ac_c2_target_unaffected_on_fsync_failure` | Yes for the authoritative cycle-5 AC in task body line 866. The tests at `serve/kanban/tests/test_storage_io.py:195` and `:208` cover replace failure and pre-replace fsync failure, matching the implementation cleanup path at `serve/kanban/src/owlbear_kanban/storage_io.py:52` and the brief pseudocode / crash-model split at `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:216`, `:229`, and `:664`. | COVERED |
| AC-C3 | `test_ac_c3_list_task_files_excludes_tmp` | Yes. `serve/kanban/src/owlbear_kanban/storage.py:364` filters hidden temp files and `serve/kanban/tests/test_storage_io.py:231` rejects `.tmp-*` entries. | COVERED |
| AC-C4 | `test_ac_c4_50_concurrent_threads_yield_distinct_ids`, `test_ac_c4_next_id_lock_file_exists_after_allocation` | Yes for the refined task scope. `serve/kanban/src/owlbear_kanban/storage.py:427` and `:431` allocate under `.next_id.lock`, the cross-process lock helper lives at `serve/kanban/src/owlbear_kanban/engine.py:277`, and the tests at `serve/kanban/tests/test_storage_io.py:253` and `:279` enforce 50 distinct IDs plus lock-file existence. | COVERED |
| AC-C4a | `test_ac_c4a_cas_20_threads_one_success_19_stale`, `test_ac_c4a_survivor_write_intact` | Yes. `serve/kanban/src/owlbear_kanban/storage.py:344` uses the per-task lock path and the tests at `serve/kanban/tests/test_storage_io.py:293` and `:332` enforce one winner, 19 stale outcomes, and intact survivor state. | COVERED |
| AC-C4b | `test_ac_c4b_lock_files_not_in_list_task_files`, `test_ac_c4b_lock_files_not_in_list_archive_files`, `test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path` | Yes. The lock path in `serve/kanban/src/owlbear_kanban/storage.py:344` plus the listing filters at `:364` and `:378` are directly exercised by the tests at `serve/kanban/tests/test_storage_io.py:366`, `:379`, and `:392`. | COVERED |
| AC-C51 | `test_ac_c51_crash_between_save_config_and_write_task` | Yes for the cycle-5 helper-scope AC at task line 866. The burned-ID behavior is asserted at `serve/kanban/tests/test_storage_io.py:412`, matches `serve/kanban/src/owlbear_kanban/storage.py:427` and `:431`, and the engine-level crash path is separately tracked by `.owlbear/kanban/tasks/1101-engine-create-task-crash-safety-test-ac-c51-engine.md:1`. | COVERED |

#### Security Review
- No issues found in scope. The reviewed paths are local filesystem write, rename, and file-lock operations only.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_AtomicWrite` | Current snapshot contains the strengthened sibling-path and platform-conditional ordering assertions described in the task history and implemented at `serve/kanban/tests/test_storage_io.py:94`, `:120`, and `:157`. No `skip` or `xfail` weakening is visible. | STRENGTHENED (current snapshot) |
| `TestFromAC_IDAllocation` | Current snapshot contains the direct `.next_id.lock` and `tasks/.<id>.lock` assertions at `serve/kanban/tests/test_storage_io.py:279` and `:392`. No `skip` or `xfail` weakening is visible. | STRENGTHENED (current snapshot) |
- Historical immutability against the original RED commit was not independently re-verified with the available tool set.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | AC-C1 now asserts sibling placement plus exact operation ordering; AC-C4 and AC-C4b assert exact lock-file locations; AC-C4a asserts exact success and stale counts. |
| Negative and error-path coverage | ADEQUATE | Replace failure and pre-replace fsync failure are covered at `serve/kanban/tests/test_storage_io.py:195` and `:208`; stale OCC behavior is covered at `:293`. |
| Manual mutation reasoning | ADEQUATE | Wrong temp directory, wrong fsync ordering, missing conditional dir-fsync, wrong `.next_id.lock` path, or wrong per-task lock path would fail the current suite. |
| Test independence | STRONG | Each case builds its own board under `tmp_path` and thread collectors are local to each test. |
| Descriptive names | STRONG | Test names map directly to the refined AC lines throughout `serve/kanban/tests/test_storage_io.py`. |

#### Data Safety
- No issues found in the refined scope. `atomic_write` still cleans and re-raises on `Exception`-subclass failures at `serve/kanban/src/owlbear_kanban/storage_io.py:52`, per-task OCC locks are in `serve/kanban/src/owlbear_kanban/storage.py:344`, and ID allocation locks are in `serve/kanban/src/owlbear_kanban/storage.py:431`.

#### Implementation-Aware Gaps
- No blocking gaps found in the cycle-5 task scope.
- Engine-level `create_task` crash safety remains out of scope for this helper task and is explicitly tracked by `.owlbear/kanban/tasks/1101-engine-create-task-crash-safety-test-ac-c51-engine.md:1`.

#### Necessity Check
- Not applicable. No new dependency, integration, or external capability was added.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 6 |
| Approach variation | Yes. The task history shows AC refinement, assertion strengthening, platform scoping, and final contract clarification rather than identical retries. |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_storage_io.py:1` still describes the file as an all-failing RED suite even though the current snapshot is green.
- The original AC block at the top of task `#1046` is stale, but the authoritative review basis is the cycle-5 refined AC recorded from `.owlbear/kanban/tasks/1046-c-01-red-storage-io-atomic-write-id-allocation-tests.md:866` onward.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C1 | `serve/kanban/src/owlbear_kanban/storage_io.py:16`, `:44`, `:46`; `serve/kanban/tests/test_storage_io.py:94`, `:120`, `:150`, `:157` | `test_ac_c1_*` | PASS |
| AC-C2 | `.owlbear/kanban/tasks/1046-c-01-red-storage-io-atomic-write-id-allocation-tests.md:866`; `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:216`, `:229`, `:664`; `serve/kanban/src/owlbear_kanban/storage_io.py:52`; `serve/kanban/tests/test_storage_io.py:195`, `:208` | `test_ac_c2_*` | PASS |
| AC-C3 | `serve/kanban/src/owlbear_kanban/storage.py:364`; `serve/kanban/tests/test_storage_io.py:231` | `test_ac_c3_list_task_files_excludes_tmp` | PASS |
| AC-C4 | `serve/kanban/src/owlbear_kanban/storage.py:427`, `:431`; `serve/kanban/src/owlbear_kanban/engine.py:277`; `serve/kanban/tests/test_storage_io.py:253`, `:279` | `test_ac_c4_*` | PASS |
| AC-C4a | `serve/kanban/src/owlbear_kanban/storage.py:344`; `serve/kanban/tests/test_storage_io.py:293`, `:332` | `test_ac_c4a_*` | PASS |
| AC-C4b | `serve/kanban/src/owlbear_kanban/storage.py:344`, `:364`, `:378`; `serve/kanban/tests/test_storage_io.py:366`, `:379`, `:392` | `test_ac_c4b_*` | PASS |
| AC-C51 | `.owlbear/kanban/tasks/1046-c-01-red-storage-io-atomic-write-id-allocation-tests.md:866`; `serve/kanban/src/owlbear_kanban/storage.py:427`, `:431`; `serve/kanban/tests/test_storage_io.py:412`; `.owlbear/kanban/tasks/1101-engine-create-task-crash-safety-test-ac-c51-engine.md:1` | `test_ac_c51_crash_between_save_config_and_write_task` | PASS |

### Deductions
- 0.03 Historical `TestFromAC_*` immutability against the original RED commit was not independently re-verified with the available tool set.
- 0.02 Stale RED-era task and test-file text increases review friction, even though the cycle-5 refined AC is authoritative and the live code matches it.

### Confidence: 0.95
### Verdict: PASS
### Action
Advance to docs.

### Post-Task Reflection
- Problem faced: The task body contains five earlier review loops and stale top-level AC text, so identifying the authoritative contract required reading the final architecture note rather than the header block.
- Workaround applied: Used both task-scoped and supplemental storage-module quality-runner passes to separate task evidence from broader storage coverage.
- Pattern discovered: Retroactive GREEN closeout is reliable when the reviewer treats the latest architect refinement as binding and verifies helper coverage with adjacent task-owned storage tests.
- Time sink: Reconstructing the authoritative AC from task history rather than from a single canonical top section.
- Quality gap: The remaining issues are documentation hygiene only, not implementation or test-contract defects.
[[2026-04-22]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | serve/kanban/README.md documents KanbanEngine public API only; no reference to atomic_write, storage_io, or internal storage layer. Test file changes do not affect API behavior. |
| 2 | Module docstrings | Yes | Updated | serve/kanban/tests/test_storage_io.py:1-6 — stale "TDD RED" / "All tests FAIL" module docstring replaced with accurate GREEN-phase description. Committed 8838e5d9. |
| 3 | External attribution | No | N/A | No external patterns used. Task is assertion-strengthening and platform-scoping of existing test file. |
| 4 | Research doc | No | N/A | No research doc produced for this task. |
| 5 | Diagram maintenance (describes match) | No | N/A | kanban.excalidraw describes serve/kanban/src/**; changed file is serve/kanban/tests/test_storage_io.py (tests/, not src/). No describes-match. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation requested in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/tests/test_storage_io.py | IN (docstrings) | Updated module docstring |

### Files Updated
- serve/kanban/tests/test_storage_io.py (module docstring only — commit 8838e5d9)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (.owlbear/scratch/1046-* — no files found)
[[2026-04-22]]
## Audit

### AC Verification (cycle 5 refined AC is authoritative)
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C1 (ordering, platform-conditional) | test_ac_c1_fsyncs_in_correct_order: sequence spy asserts [fsync_file, replace, fsync_dir] when O_DIRECTORY available, [fsync_file, replace] otherwise. Sibling placement verified in test_ac_c1_writes_via_tmp_sibling. skipif guard on test_ac_c1_posix_fsyncs_file_and_dir. | PASS |
| AC-C2 (Exception-subclass scope) | test_ac_c2_cleans_up_tmp_on_replace_failure and test_ac_c2_target_unaffected_on_fsync_failure cover pre-commit-point cleanup. storage_io.py:52 uses except Exception per brief pseudocode. | PASS |
| AC-C3 | test_ac_c3_list_task_files_excludes_tmp exercises storage.py:364 hidden/temp filter. | PASS |
| AC-C4 (lock-file existence) | test_ac_c4_50_concurrent_threads_yield_distinct_ids enforces 50 unique IDs. test_ac_c4_next_id_lock_file_exists_after_allocation verifies .next_id.lock file exists. | PASS |
| AC-C4a | test_ac_c4a_cas_20_threads_one_success_19_stale and test_ac_c4a_survivor_write_intact enforce exact counts and survivor readback. | PASS |
| AC-C4b | test_ac_c4b_lock_files_not_in_list_task_files, test_ac_c4b_lock_files_not_in_list_archive_files, and test_ac_c4b_write_task_if_unchanged_creates_lock_at_per_task_path verify listing exclusion and tasks/.<id>.lock location. | PASS |
| AC-C51 (helper scope) | test_ac_c51_crash_between_save_config_and_write_task asserts next_id == original+1, config == original+2, no burned task file. Engine crash safety tracked in #1101. | PASS |

### Test Results
- Full suite (quality-runner mode=full): 1217 passed, 106 failed, 4 skipped. All 106 failures are outside task scope (mcp-kanban model imports, cockpit tests, session records, yaml loader, react compiler, mcp-knowledge schema). Zero failures in serve/kanban/tests/test_storage_io.py or related storage files.
- Task-scoped: 15 passed, 0 failed per reviewer evidence.
- Supplemental storage-module: 78 passed, 0 failed per reviewer evidence.
- Lint: task-scoped files clean. 5 W292 violations in unrelated test files.

### Reviewer Evidence
Present and detailed across 6 review cycles. Final cycle: PASS at 0.95 confidence with all 7 AC lines PASS, STRONG/ADEQUATE test quality, no security or data-safety issues. Trusted for code-level findings.

### Architect Quality: 3/5
Original AC had wrong C51 math (+2 vs correct +1), ambiguous C2 scope ("any exception" vs Exception-subclass), and overloaded C4b (config scope mixed with Python scope). Required 5 architect refinement cycles to stabilize. Implementation was correct throughout; the review loop was driven entirely by AC imprecision and test assertion quality, not code defects.

### Deduction Breakdown
| Criterion | Deduction |
|-----------|-----------|
| AC lines without evidence | 0 (all 7 verified) |
| Lint violations in task scope | 0 (clean) |
| AC quality score 3/5 | -0.03 |
| Missing reviewer evidence | 0 (detailed, PASS) |
| Full-suite failures in task scope | 0 (none) |

### Confidence: 0.97
### Action: Archive

### Commits (from task history)
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| de06fa41 | test | test_storage_io.py | #1046 |
| ac7cb6e1 | feat | storage_io.py, storage.py | #1046 |
| 8d51932c | test | test_storage_io.py | #1046 |
| f992689d | test | test_storage_io.py | #1046 |
| 37bb8027 | test | test_storage_io.py | #1046 |
| 8838e5d9 | docs | test_storage_io.py | #1046 |