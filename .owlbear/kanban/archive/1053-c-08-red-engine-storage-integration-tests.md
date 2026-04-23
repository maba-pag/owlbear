---
id: 1053
title: 'C-08: RED — engine storage-integration tests'
status: backlog
priority: needed
created: 2026-04-21T10:42:50.306120+00:00
updated: 2026-04-22T06:45:29.062304+00:00
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
Brief C (#1043) — paper-c.md §8.4, §8.5, §8.11
Module: `serve/kanban/tests/test_engine_storage.py`

## Acceptance Criteria

- [ ] AC-C19: `list_tasks` SKIPS files failing modes 1, 3-9 silently
- [ ] AC-C20: `list_tasks` HARD-RAISES `CorruptionError(code="ERR_CORRUPT_DUPLICATE_ID")` for mode 2
- [ ] AC-C23: `sweep()` returns `list[int]` of released claim IDs only
- [ ] AC-C24: `repair_storage()` quarantines corrupt files via §4.4 sequence; file moved BEFORE AR creation attempt
- [ ] AC-C25: `repair_storage()` records `RepairOutcome(action="failed")` if AR creation fails; file remains quarantined
- [ ] AC-C26: `repair_storage()` resolves `ERR_CORRUPT_DUPLICATE_LOCATION` by archive-wins
- [ ] AC-C27: `sweep()` reconciles claim timeouts independently of corruption repair
- [ ] AC-C47: `KanbanEngine.__init__` raises `MigrationRequiredError(code="ERR_MIGRATION_REQUIRED")` if any `tasks/` file contains `claimed_by`
- [ ] AC-C49: `_parse_duration("30m")` returns `timedelta(minutes=30)`; malformed inputs raise `ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT")`
- [ ] AC-C50: `BoardConfig` validation calls `_parse_duration(claim_timeout)` at config load time (eager validation)
- [ ] AC-C52: `sweep()` releasing expired claim does NOT mutate task body; only `claimed_at` cleared and `updated` advanced
- [ ] AC-C54: AR creation by `repair_storage()` uses `body=str` (markdown), no `status` argument; verify against Brief B `create_task` signature
- [ ] All tests fail (RED phase — no implementation exists yet)
[[2026-04-21]]
## Test-Writer Notes
- Test file: serve/kanban/tests/test_engine_storage.py
- Classes: TestFromAC_ListTasksCorruption, TestFromAC_Sweep, TestFromAC_RepairStorage, TestFromAC_MigrationGate, TestFromAC_ParseDuration, TestFromAC_ARCreationSignature
- Context: 20 previously committed tests were already GREEN (implementation was complete). Audited all AC coverage and found two genuine gaps in AC-C19: `list_tasks()` has no mode-6 (id-filename mismatch) or mode-9 (invalid priority) checks — both classes of corrupt files pass through silently instead of being skipped. Added 2 failing tests targeting these gaps.
- Tests per category: happy 6, edge 8, error 6, boundary 2
- Total: 22 tests — 20 PASS (existing GREEN), 2 FAIL (new RED)
- New failing tests:
  - test_ac_c19_list_tasks_skips_mode6_id_filename_mismatch — FAIL (mode 6 not filtered)
  - test_ac_c19_list_tasks_skips_mode9_invalid_priority — FAIL (mode 9 not filtered)
- ruff: clean
- AC coverage: C19 (now fully covered incl. modes 6+9), C20, C23, C24, C25, C26, C27, C47, C49, C50, C52, C54 — all covered
[[2026-04-22]]
## Builder Notes
- Implementation: no source edits required in this retry; existing logic already covers mode-6 and mode-9 corruption filtering in list_tasks path.
- Files changed: none.
- Tests: 22 TestFromAC tests passed in `serve/kanban/tests/test_engine_storage.py`.
- Coverage: scoped quality-runner report showed 37% overall in the kanban package for this run (no new code touched).
- ruff: clean (target test file and engine lint path checks are clean).
- Evidence summary: quality-runner scoped run returned `failed: []`, including the two prior RED cases (`id-filename mismatch`, `invalid priority`) now green under current implementation.
- Fixes applied: none in this attempt; verification-only retry confirmed expected behavior.
[[2026-04-22]]
## Review Evidence

### Tests
- Quality-runner scoped pytest on `serve/kanban/tests/test_engine_storage.py`: 22 passed, 0 failed, 0 skipped.
- Initial combined quality-runner run returned a ruff execution interruption (exit 130). Scoped lint retry on `serve/kanban/src/owlbear_kanban/engine.py` and `serve/kanban/tests/test_engine_storage.py` was clean and is treated as the authoritative lint result.
- Coverage from the scoped run was low for the target implementation surface: overall 37%; `owlbear_kanban.engine` 38%; `owlbear_kanban.models` 93%; `owlbear_kanban.task_io` 80%; `owlbear_kanban.config_loader` 96%.

### Lint
- Clean on scoped retry.

### AC Compliance
| AC | Evidence | Status |
| --- | --- | --- |
| AC-C19 | `TestFromAC_ListTasksCorruption` covers mode 1, mode 6, mode 8, and mode 9 only. The test named `test_ac_c19_list_tasks_skips_all_non_mode2_corrupt` creates only a mode-8 invalid-status file. There are no `TestFromAC_*` cases for corruption modes 3, 4, 5, or 7. Separately, `ERR_CORRUPT_DUPLICATE_LOCATION` appears only in repair logic in `corruption.py`, not the `list_tasks` path. | MISSING |
| AC-C20 | Duplicate-ID test asserts `CorruptionError` and exact code `ERR_CORRUPT_DUPLICATE_ID`. | COVERED |
| AC-C23 | Tests assert `sweep()` returns `list[int]` and contains only released expired IDs. | COVERED |
| AC-C24 | Spy proves the corrupt file is already quarantined when `create_task()` is entered, but does not verify the full §4.4 sequence. | LAX |
| AC-C25 | Failure-path test forces AR creation failure, checks for at least one `RepairOutcome(action="failed")`, and confirms the file remains quarantined. | COVERED |
| AC-C26 | Test proves archive-wins end state, but not that the `ERR_CORRUPT_DUPLICATE_LOCATION` branch was the path exercised. | LAX |
| AC-C27 | Test proves expired claims are released while corrupt files remain untouched and no quarantine is created. | COVERED |
| AC-C47 | Tests cover raise, no-raise control, and exact `ERR_MIGRATION_REQUIRED` code. | COVERED |
| AC-C49 | Tests cover valid duration parsing and malformed input raising `ConfigError(code="ERR_INVALID_CLAIM_TIMEOUT")`. | COVERED |
| AC-C50 | Tests prove eager load-time failure/success, but not the exact implementation-path claim that `BoardConfig` validation itself calls `_parse_duration`. | LAX |
| AC-C52 | Current test checks only `claimed_at` clearing and body-text preservation. It does not assert that `updated` advances, and it does not assert that no extra frontmatter fields were written. The implementation also clears `record.claimed_by` in `sweep()` and writes through `task_io.write_task`, which serializes `record.model_dump()`. That means this AC can be violated while the current test still passes. | VIOLATION |
| AC-C54 | Spy proves `body` is a string, but it cannot distinguish omitted `status` from an explicitly passed empty-string `status`. | LAX |

### Critical Findings
- `AC-C19` is not fully covered by `TestFromAC_*`. The task body claims silent skip behavior for modes 1 and 3-9, but the suite only exercises 1, 6, 8, and 9. A regression in modes 3, 4, 5, or 7 would still pass review.
- `AC-C52` is both weakly tested and likely broken in implementation. `engine.py` imports `write_task` from `task_io.py`, not the higher-level storage writer. In `sweep()`, the code clears `record.claimed_by` and then writes the full model back to disk. Because `Task.claimed_by` is part of the model and `task_io.write_task` serializes `record.model_dump()`, the expired-claim path can rewrite frontmatter beyond `claimed_at` and `updated`, contradicting the AC wording.
- Test quality is below review threshold: negative/error-path coverage is weak for `AC-C19`, and manual-mutation resistance is weak for `AC-C52` and `AC-C54`.

### Deductions
- 0.20 deduction: `AC-C19` missing `TestFromAC_*` coverage for corruption modes 3, 4, 5, and 7.
- 0.16 deduction: `AC-C52` implementation path can mutate frontmatter beyond the allowed fields, while the current test would still pass.
- 0.08 deduction: `AC-C54` assertion does not actually prove omission of the `status` argument.
- 0.05 deduction: `AC-C24`, `AC-C26`, and `AC-C50` are only partially pinned by the current assertions.
- 0.03 deduction: scoped coverage on the target engine surface remains low.

### Verdict
- FAIL
- Confidence: 0.48
- Routing: return to `todo`

### Action
- Test-writer should add `TestFromAC_*` coverage for `AC-C19` modes 3, 4, 5, and 7.
- Test-writer should strengthen `AC-C52` to assert `updated` advances and that the serialized task file does not gain any extra frontmatter mutation beyond `claimed_at` clearing.
- Test-writer should strengthen `AC-C54` so omission of the `status` argument is observable, not inferred from a default parameter.
- Builder should then re-run against the stronger suite; the `AC-C52` writer-path issue is likely to fail once those assertions exist.

### Post-task Reflection
- The first quality-runner pass mixed trustworthy pytest evidence with a transient lint interruption; a narrower scoped lint retry separated tooling noise from actual task quality.
- A combined AC label can hide missing subcases. `AC-C19` looked complete at a glance until each corruption mode was mapped back to a concrete `TestFromAC_*` method.
- Writer-path checks matter in this package: `engine.py` and `storage.py` do not share the same serialization guarantees.
- Passing integration tests were not sufficient evidence here because the strongest contract risk was a frontmatter mutation the suite never asserted.
[[2026-04-22]]
## Test-Writer Notes
- Retry: reviewer cited missing AC-C19 coverage (modes 3, 4, 5, 7), weak AC-C52, and weak AC-C54.
- Test file: `serve/kanban/tests/test_engine_storage.py`
- **7 new tests added** (total now 29 tests):

### New tests added to existing classes:

**`TestFromAC_ListTasksCorruption`** (AC-C19 modes 3, 4, 5, 7):
- `test_ac_c19_list_tasks_skips_mode3_missing_required_field` — PASS (detect_corruption handles mode 3)
- `test_ac_c19_list_tasks_skips_mode4_type_mismatch_id_string` — PASS (detect_corruption handles mode 4)
- `test_ac_c19_list_tasks_skips_mode5_yaml_parse_error` — PASS (detect_corruption handles mode 5)
- `test_ac_c19_list_tasks_skips_mode7_duplicate_location` — **FAIL** ✓ (detect_corruption doesn't check cross-directory; list_tasks currently returns the task instead of skipping it)

**`TestFromAC_Sweep`** (AC-C52 strengthened):
- `test_ac_c52_sweep_advances_updated_timestamp` — PASS (implementation already advances updated)
- `test_ac_c52_sweep_does_not_serialize_claimed_by_to_file` — **FAIL** ✓ (task_io.write_task serializes model_dump() including claimed_by: null, which adds the field to files that didn't originally contain it)

**`TestFromAC_ARCreationSignature`** (AC-C54 strengthened):
- `test_ac_c54_status_not_explicitly_passed_in_create_task_kwargs` — PASS (uses **kwargs capture to distinguish omitted status from explicit status=""; current implementation omits it)

### Run summary:
- Total: 29 tests — 27 PASS, 2 FAIL
- ruff: clean
- AC coverage: C19 (all 9 modes covered), C20, C23, C24, C25, C26, C27, C47, C49, C50, C52, C54
[[2026-04-22]]
## Builder Notes
- Files changed: `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/src/owlbear_kanban/task_io.py`.
- Implementation:
  - `list_tasks()` now skips `tasks/` entries when the same numeric ID already exists in `archive/` (mode-7 duplicate-location behavior for AC-C19).
  - `task_io.write_task()` now omits `claimed_by` from serialized frontmatter, preventing sweep-release writes from introducing that legacy field (AC-C52).
- Tests: `serve/kanban/tests/test_engine_storage.py` scoped run: 29 passed, 0 failed, 0 skipped.
- Lint: scoped ruff on touched source files + test file: clean.
- Coverage (scoped): overall 38%; `owlbear_kanban.engine` 39%; `owlbear_kanban.task_io` 80%.
- Evidence summary: both previously failing TestFromAC cases now pass:
  - `test_ac_c19_list_tasks_skips_mode7_duplicate_location`
  - `test_ac_c52_sweep_does_not_serialize_claimed_by_to_file`
- Commit: `2712e0f8` (`feat: implement storage integration fixes (#1053, builder)`).

### Post-task Reflection
- The duplicate-location behavior gap was not in corruption scan-and-fix; it was specifically in the `list_tasks()` read path.
- Reusing `task_io.write_task()` for sweep updates required matching storage serialization guarantees to avoid schema drift.
- A scoped quality-runner rerun immediately exposed a symbol-resolution regression (`F821`), which was fixed with local filename ID parsing.
- Keeping the fix to two source files was sufficient to satisfy the strengthened RED tests without API changes.
[[2026-04-22]]
## Review Evidence
### Test Results
- pytest (quality-runner scoped on serve/kanban/tests/test_engine_storage.py): 29 passed, 0 failed, 0 skipped.

### Lint
- Clean on scoped paths: serve/kanban/src/owlbear_kanban/engine.py, serve/kanban/src/owlbear_kanban/task_io.py, serve/kanban/tests/test_engine_storage.py.

### Coverage
- overall: 38%
- owlbear_kanban.engine: 39%
- owlbear_kanban.task_io: 80%

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C19 | TestFromAC_ListTasksCorruption in serve/kanban/tests/test_engine_storage.py:133-308, including mode 3 at :221, mode 7 at :287, and mode 9 at :199 | Yes for the listed modes. I did not count the code-reader cache concern because detect_corruption rejects invalid status before cache insert (serve/kanban/src/owlbear_kanban/corruption.py:275-283; serve/kanban/src/owlbear_kanban/engine.py:507-542). | COVERED |
| AC-C20 | test_ac_c20_list_tasks_hard_raises_on_duplicate_id at serve/kanban/tests/test_engine_storage.py:169-180; raise path at serve/kanban/src/owlbear_kanban/engine.py:551-557 | Yes. | COVERED |
| AC-C23 | test_ac_c23_sweep_returns_list_of_int at serve/kanban/tests/test_engine_storage.py:321-327 and test_ac_c23_sweep_returns_only_released_ids at :330-347 | No. The main contract test uses membership assertions only at :346-347, so extra unexpected IDs would still pass. | LAX |
| AC-C24 | test_ac_c24_file_moved_before_ar_creation at serve/kanban/tests/test_engine_storage.py:459-479; repair path at serve/kanban/src/owlbear_kanban/engine.py:1111-1157 | Partially. It proves move-before-AR-call ordering, but not the full §4.4 quarantine sequence delegated into scan_and_fix. | LAX |
| AC-C25 | test_ac_c25_repair_records_failed_when_ar_creation_fails at serve/kanban/tests/test_engine_storage.py:481-500; failure branch at serve/kanban/src/owlbear_kanban/engine.py:1148-1156 | Yes. | COVERED |
| AC-C26 | test_ac_c26_duplicate_location_resolved_archive_wins at serve/kanban/tests/test_engine_storage.py:502-514; duplicate-location fix path at serve/kanban/src/owlbear_kanban/engine.py:534-538 and corruption.py:353-360 | Yes at observable behavior level. | COVERED |
| AC-C27 | test_ac_c27_sweep_independent_of_corruption_repair at serve/kanban/tests/test_engine_storage.py:349-367; silent skip in serve/kanban/src/owlbear_kanban/engine.py:1085-1090 | Yes. | COVERED |
| AC-C47 | migration-gate tests at serve/kanban/tests/test_engine_storage.py:526-560; constructor gate at serve/kanban/src/owlbear_kanban/engine.py:314-370 | Yes. | COVERED |
| AC-C49 | parse-duration tests at serve/kanban/tests/test_engine_storage.py:571-599; parser at serve/kanban/src/owlbear_kanban/engine.py:56-75 | Yes. | COVERED |
| AC-C50 | load-time tests at serve/kanban/tests/test_engine_storage.py:601-616 | No. The tests prove only that load_config raises on bad input, not that BoardConfig validation itself calls _parse_duration. Current load path is config_loader.load_config -> BoardConfig.model_validate at serve/kanban/src/owlbear_kanban/config_loader.py:58, then storage.load_config -> _validate_claim_timeout at serve/kanban/src/owlbear_kanban/storage.py:109-114. _parse_duration lives at serve/kanban/src/owlbear_kanban/engine.py:56 and is not part of the config-load path. | LAX |
| AC-C52 | sweep tests at serve/kanban/tests/test_engine_storage.py:369-445; sweep write path at serve/kanban/src/owlbear_kanban/engine.py:1102-1106; serializer at serve/kanban/src/owlbear_kanban/task_io.py:228-249 | No. updated is asserted at :415 and claimed_by omission at :445, but the body check at :391 is substring-only, so appended or prefixed body mutations would still pass. | LAX |
| AC-C54 | kwargs-spy test at serve/kanban/tests/test_engine_storage.py:668-691; AR create call at serve/kanban/src/owlbear_kanban/engine.py:1143-1147; create_task signature at :646-653 | Yes. The kwargs spy correctly proves status omission rather than default-value inference. | COVERED |
| RED-phase historical gate | Test-Writer note in task body recorded 27 passed / 2 failed before builder retry. | Historical only; satisfied earlier in the cycle. | COVERED |

#### Security Review
- No security issues found in the scoped implementation. The reviewed paths are local filesystem and task-state transitions only; no shell, SQL, template, eval, or secret-handling sink appears in serve/kanban/src/owlbear_kanban/engine.py:452-1157 or serve/kanban/src/owlbear_kanban/task_io.py:228-266.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC_* suite in serve/kanban/tests/test_engine_storage.py | No builder edits in the current retry. Builder changed only serve/kanban/src/owlbear_kanban/engine.py and serve/kanban/src/owlbear_kanban/task_io.py. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | AC-C23 uses membership-only assertions at serve/kanban/tests/test_engine_storage.py:346-347. AC-C52 uses a substring body check at :391. Both leave false-green space. |
| Negative and error-path coverage | ADEQUATE | Duplicate-ID, AR-failure, migration-required, and malformed-duration cases are explicitly exercised at serve/kanban/tests/test_engine_storage.py:169-180, :481-500, :526-540, and :592-611. |
| Manual mutation reasoning | WEAK | AC-C50 remains green even though config load currently validates via storage._validate_claim_timeout (serve/kanban/src/owlbear_kanban/storage.py:109-114) rather than BoardConfig -> _parse_duration (serve/kanban/src/owlbear_kanban/config_loader.py:58; serve/kanban/src/owlbear_kanban/engine.py:56-75). |
| Test independence | STRONG | Each test builds a fresh board under tmp_path via helper setup at serve/kanban/tests/test_engine_storage.py:117-123 and then instantiates a fresh engine, e.g. :142, :324, :383, :474. |
| Descriptive test names | STRONG | Test names are AC-specific and behavior-specific throughout serve/kanban/tests/test_engine_storage.py:133-691. |

#### Data Safety
- No scoped data-safety issues confirmed. I did not count the code-reader's suggested AC-C19 cache-poisoning scenario because detect_corruption rejects invalid status before cache population in the non-archived path.

#### Implementation-Aware Gaps
- AC-C50 is not satisfied as written. BoardConfig declares claim_timeout as a plain field at serve/kanban/src/owlbear_kanban/models.py:55, and the only BoardConfig model validator in scope is the legacy normalizer at :78-99. config_loader.load_config returns BoardConfig.model_validate(...) at serve/kanban/src/owlbear_kanban/config_loader.py:58, after which storage.load_config applies a separate regex check at serve/kanban/src/owlbear_kanban/storage.py:109-114. No config-load path invokes _parse_duration from serve/kanban/src/owlbear_kanban/engine.py:56-75.
- Touched-module coverage remains below the review bar: owlbear_kanban.engine 39%, owlbear_kanban.task_io 80%.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 2 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- I rejected one code-reader concern after direct verification: AC-C19 does not currently admit invalid-status cache poisoning because detect_corruption returns before read_task/cache insertion on the non-archived path.
- Minor documentation drift remains: task_io.write_task says extra fields survive round-trips, but claimed_by is intentionally stripped in serve/kanban/src/owlbear_kanban/task_io.py:240-249.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C19 | list_tasks now skips duplicate-location tasks/ entries before returning results (serve/kanban/src/owlbear_kanban/engine.py:534-538), and the retry suite covers modes 1 and 3-9 in serve/kanban/tests/test_engine_storage.py:133-308. | TestFromAC_ListTasksCorruption | PASS |
| AC-C20 | Duplicate IDs raise CorruptionError at serve/kanban/src/owlbear_kanban/engine.py:551-557. | test_ac_c20_list_tasks_hard_raises_on_duplicate_id | PASS |
| AC-C23 | sweep returns released IDs via released.append(record.id) at serve/kanban/src/owlbear_kanban/engine.py:1106, but the AC proof is weak because the test only checks membership at serve/kanban/tests/test_engine_storage.py:346-347. | test_ac_c23_sweep_returns_only_released_ids | FAIL |
| AC-C24 | repair_storage delegates file move before AR creation and the spy confirms quarantine exists when create_task is entered (serve/kanban/tests/test_engine_storage.py:459-479; serve/kanban/src/owlbear_kanban/engine.py:1128-1147). | test_ac_c24_file_moved_before_ar_creation | PASS |
| AC-C25 | repair_storage records failed outcomes on AR creation exceptions at serve/kanban/src/owlbear_kanban/engine.py:1148-1156. | test_ac_c25_repair_records_failed_when_ar_creation_fails | PASS |
| AC-C26 | archive-wins behavior is now reflected in list_tasks and repair behavior; tasks/ copy is removed/fixed while archive survives (serve/kanban/tests/test_engine_storage.py:502-514; serve/kanban/src/owlbear_kanban/corruption.py:353-360). | test_ac_c26_duplicate_location_resolved_archive_wins | PASS |
| AC-C27 | corrupt files are skipped in sweep without quarantine mutation at serve/kanban/src/owlbear_kanban/engine.py:1085-1090. | test_ac_c27_sweep_independent_of_corruption_repair | PASS |
| AC-C47 | constructor scans tasks frontmatter and raises MigrationRequiredError on claimed_by at serve/kanban/src/owlbear_kanban/engine.py:337-370. | TestFromAC_MigrationGate | PASS |
| AC-C49 | _parse_duration parses valid values and raises ConfigError on malformed input at serve/kanban/src/owlbear_kanban/engine.py:56-75. | TestFromAC_ParseDuration | PASS |
| AC-C50 | Current implementation validates claim_timeout after BoardConfig.model_validate using storage._validate_claim_timeout instead of BoardConfig -> _parse_duration, contrary to the AC wording (serve/kanban/src/owlbear_kanban/config_loader.py:58; serve/kanban/src/owlbear_kanban/storage.py:109-114; serve/kanban/src/owlbear_kanban/engine.py:56-75). | test_ac_c50_board_config_eager_validation_on_load | FAIL |
| AC-C52 | sweep clears claimed_at and updates updated at serve/kanban/src/owlbear_kanban/engine.py:1102-1104, and claimed_by is stripped on write at serve/kanban/src/owlbear_kanban/task_io.py:249, but the current body-preservation proof is insufficient because the assertion at serve/kanban/tests/test_engine_storage.py:391 is substring-only. | TestFromAC_Sweep | FAIL |
| AC-C54 | repair_storage omits status and passes body as str in the unbound create_task call at serve/kanban/src/owlbear_kanban/engine.py:1143-1147. | test_ac_c54_status_not_explicitly_passed_in_create_task_kwargs | PASS |
| RED-phase historical gate | Prior Test-Writer note recorded 2 failing tests before the builder retry. | Historical task-body evidence | PASS |

### Deductions
- 0.18 deduction: AC-C50 implementation path does not match the stated contract, and the current TestFromAC check would not catch it.
- 0.12 deduction: AC-C23 exact-return contract is weakly asserted.
- 0.10 deduction: AC-C52 exact body-preservation contract is weakly asserted.
- 0.08 deduction: touched-module coverage is below the 90% review target.
- 0.04 deduction: AC-C24 evidence is partial on the full §4.4 sequence.

### Confidence: 0.48
### Verdict: FAIL
### Routing: todo
### Action
- Test-writer should tighten AC-C23 to assert the exact released-ID set, not just membership.
- Test-writer should tighten AC-C52 to assert exact body equality, not substring containment.
- Test-writer should add an AC-C50 assertion that distinguishes BoardConfig/config-load invocation of _parse_duration from the current wrapper-level regex check.
- Builder should rerun only after the stronger TestFromAC suite is in place; AC-C50 is likely to fail immediately once that contract is pinned.

### Post-task Reflection
- Green execution was not sufficient evidence here because one AC named a specific validation mechanism and the suite only checked equivalent outward behavior.
- The code-reader surfaced a plausible AC-C19 concern, but direct source verification showed it was a false alarm; independent confirmation mattered.
- Membership and substring assertions are still the fastest way for a TestFromAC suite to drift into false-green territory.
- Coverage on touched modules stayed well below the review target even though the scoped task suite was green.
[[2026-04-22]]
## Test-Writer Notes
- Retry: reviewer cited weak AC-C23, weak AC-C52, and missing AC-C50 mechanism test.
- Test file: `serve/kanban/tests/test_engine_storage.py`
- **3 new tests added** (total now 32 tests):

### New tests added to existing classes:

**`TestFromAC_Sweep`** (AC-C23 and AC-C52 tightened):
- `test_ac_c23_sweep_returns_exact_released_id_set` — PASS (set-equality `== {1001, 1002}` pins the exact released-ID contract; two expired + one unclaimed task)
- `test_ac_c52_sweep_preserves_body_exactly` — PASS (strict `==` equality on body string; implementation already preserves body exactly)

**`TestFromAC_ParseDuration`** (AC-C50 mechanism test):
- `test_ac_c50_config_load_calls_parse_duration_not_only_regex` — **FAIL** ✓ (`assert_called_once()` fails: `_parse_duration` called 0 times; current implementation uses `config_loader._validate_claim_timeout` (regex) instead of `engine._parse_duration`)

### Run summary:
- Total: 32 tests — 31 PASS, **1 FAIL**
- ruff: clean
- Commit: `63653263`

### AC coverage:
| AC | Status |
|----|--------|
| AC-C19 | COVERED (modes 1, 3-9 explicitly tested) |
| AC-C20 | COVERED |
| AC-C23 | COVERED (exact set-equality, not just membership) |
| AC-C24 | COVERED |
| AC-C25 | COVERED |
| AC-C26 | COVERED |
| AC-C27 | COVERED |
| AC-C47 | COVERED |
| AC-C49 | COVERED |
| AC-C50 | FAILING (new test proves `_parse_duration` not called from config-load path) |
| AC-C52 | COVERED (exact body equality + claimed_by omission + updated advance) |
| AC-C54 | COVERED |
[[2026-04-22]]
## Builder Notes
- Implementation: [serve/kanban/src/owlbear_kanban/config_loader.py](serve/kanban/src/owlbear_kanban/config_loader.py)
- Change summary: replaced regex-based claim-timeout check with canonical parser delegation (`_parse_duration`) in the eager config validation chain.
- Tests: 32 TestFromAC tests passed in [serve/kanban/tests/test_engine_storage.py](serve/kanban/tests/test_engine_storage.py)
- Coverage: 57% on `owlbear_kanban.config_loader` in scoped run (overall scoped run: 37%)
- ruff: clean on scoped paths
- Evidence summary: previously failing `TestFromAC_ParseDuration::test_ac_c50_config_load_calls_parse_duration_not_only_regex` is now green; quality-runner reported `failed: []`, `clean: true`.
- Commit: `5274d403` (`fix: route config timeout validation through parser (#1053, builder)`)

### Post-task Reflection
- Reusing the canonical parser removes duplicated duration grammar and aligns validation semantics in one place.
- The smallest safe fix was to swap validation implementation rather than moving validators across modules.
- Scoped quality-runner evidence was sufficient to confirm the AC-C50 mechanism regression and verify the GREEN transition.
[[2026-04-22]]
## Review Evidence

### Tests
- Quality-runner scoped pytest on `serve/kanban/tests/test_engine_storage.py`: 32 passed, 0 failed, 0 skipped.

### Lint
- Quality-runner scoped lint on `serve/kanban/src/owlbear_kanban/config_loader.py` and `serve/kanban/tests/test_engine_storage.py`: clean.
- VS Code diagnostics on `serve/kanban/src/owlbear_kanban/config_loader.py`, `serve/kanban/src/owlbear_kanban/storage.py`, and `serve/kanban/tests/test_engine_storage.py`: no errors.

### Coverage
- overall: 37%
- `owlbear_kanban.config_loader`: 57%

### AC Compliance
| AC | Evidence | Status |
| --- | --- | --- |
| AC-C19 | `TestFromAC_ListTasksCorruption` covers modes 1 and 3-9 in `serve/kanban/tests/test_engine_storage.py:133-308`. | PASS |
| AC-C20 | `test_ac_c20_list_tasks_hard_raises_on_duplicate_id` asserts exact `ERR_CORRUPT_DUPLICATE_ID` in `serve/kanban/tests/test_engine_storage.py:169-180`. | PASS |
| AC-C23 | `test_ac_c23_sweep_returns_exact_released_id_set` asserts exact released IDs in `serve/kanban/tests/test_engine_storage.py:349-379`. | PASS |
| AC-C24 | `test_ac_c24_file_moved_before_ar_creation` only proves the quarantine destination exists before `create_task()` in `serve/kanban/tests/test_engine_storage.py:517-540`; it does not prove the original file is already gone at that moment. | LAX |
| AC-C25 | `test_ac_c25_repair_records_failed_when_ar_creation_fails` forces AR creation failure and requires a `failed` outcome plus a quarantined file in `serve/kanban/tests/test_engine_storage.py:542-561`. | PASS |
| AC-C26 | `test_ac_c26_duplicate_location_resolved_archive_wins` asserts archive survives and tasks copy is gone in `serve/kanban/tests/test_engine_storage.py:563-577`. | PASS |
| AC-C27 | `test_ac_c27_sweep_independent_of_corruption_repair` keeps the corrupt file in `tasks/` and no `quarantine/` in `serve/kanban/tests/test_engine_storage.py:381-399`. | PASS |
| AC-C47 | Migration gate tests in `serve/kanban/tests/test_engine_storage.py:584-610` cover raise, no-raise, and exact `ERR_MIGRATION_REQUIRED`. | PASS |
| AC-C49 | Parse-duration tests in `serve/kanban/tests/test_engine_storage.py:629-660` cover valid values and exact `ERR_INVALID_CLAIM_TIMEOUT`. | PASS |
| AC-C50 | FAIL. `BoardConfig.claim_timeout` is a plain field in `serve/kanban/src/owlbear_kanban/models.py:55`, and the only BoardConfig validator in that model is the legacy normalizer at `serve/kanban/src/owlbear_kanban/models.py:78-99`. `serve/kanban/src/owlbear_kanban/config_loader.py:58` returns `BoardConfig.model_validate(...)` immediately. The parser hook is separate at `serve/kanban/src/owlbear_kanban/config_loader.py:61-65`. The actual engine path imports `load_config` from `config_loader` at `serve/kanban/src/owlbear_kanban/engine.py:39` and uses it in `KanbanEngine.__init__` at `serve/kanban/src/owlbear_kanban/engine.py:328`, so constructor-time config loading still bypasses `_parse_duration()`. The current TestFromAC only spies `storage.load_config()` in `serve/kanban/tests/test_engine_storage.py:680-694`, so this real load path is not exercised. | FAIL |
| AC-C52 | Sweep mutation tests now cover `claimed_at` clearing, `updated` advance, exact body equality, and `claimed_by` omission in `serve/kanban/tests/test_engine_storage.py:401-506`. | PASS |
| AC-C54 | `test_ac_c54_status_not_explicitly_passed_in_create_task_kwargs` proves status omission via captured kwargs in `serve/kanban/tests/test_engine_storage.py:745-770`. | PASS |
| RED-phase historical gate | Earlier task-body evidence recorded a failing RED phase before builder retries. | PASS |

### Critical Findings
- AC-C50 is still not satisfied on the actual engine config-load path. The builder retry made the storage wrapper call `_parse_duration()`, but `KanbanEngine.__init__` still loads config through `config_loader.load_config()`, which returns immediately after `BoardConfig.model_validate(...)` without any `claim_timeout` parser validation.
- The current AC-C50 test is green for the wrong reason. It exercises `storage.load_config()` only, so it cannot catch the constructor-path violation above.

### Deductions
- 0.30 deduction: AC-C50 implementation still misses the constructor/config-loader path used by `KanbanEngine`.
- 0.10 deduction: AC-C50 TestFromAC scope does not cover the actual load path named by the AC.
- 0.06 deduction: AC-C24 move-before-AR proof is partial.
- 0.06 deduction: touched-module coverage remains below the 90% review target (`owlbear_kanban.config_loader` 57%).

### Verdict
- FAIL
- Confidence: 0.48
- Routing: backlog
- Reason: third review rejection on the same task; loop-breaker applies.

### Action
- Builder or architect must move `claim_timeout` validation into the actual BoardConfig/config-loader path used by `KanbanEngine`, or narrow the AC if only the storage wrapper is intended to own validation.
- Test-writer must add a failing AC-C50 check on the real constructor/load path, for example invalid `claim_timeout` through `KanbanEngine(kanban_dir)` and/or direct `config_loader.load_config()`.
- Test-writer should tighten AC-C24 so it proves the original corrupt file is already gone before AR creation, not only that the quarantine destination exists.

### Post-task Reflection
- A green wrapper-level test can still miss the real production call chain when the engine imports a lower-level loader directly.
- The latest builder fix aligned one API path with the AC, but not the path actually used by `KanbanEngine`.
- On a third review cycle, loop-breaker routing matters more than squeezing in another local retry.