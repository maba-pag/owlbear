---
id: 1061
title: 'C-16: GREEN — kanban-migrate entry point'
status: in-progress
priority: important
created: 2026-04-21T10:44:12.239610+00:00
updated: 2026-04-23T23:08:25.432126+00:00
tags:
- phase:storage
- brief:c
- scope:kanban
- tdd:green
parent: 1043
depends_on:
- 1052
- 1059
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---
## Brief
Brief C (#1043) — paper-c.md §5, §8.7, §8.11
Module: `serve/kanban/src/owlbear_kanban/migrate.py`
Entry point: `kanban-migrate` registered in `serve/kanban/pyproject.toml`

Depends on storage surface (#1059) for atomic_write, read_task, write_task, frontmatter canonicalisation.

## Acceptance Criteria

- [ ] AC-C31: `uv run kanban-migrate` registered as console script in `serve/kanban/pyproject.toml`
- [ ] AC-C32: `--lane tasks|archive|config|all` runs only selected lane; `--lane all` runs all three
- [ ] AC-C33: Per-lane algorithms match §5.3 (tasks, archive) and §5.4 (config) exactly
- [ ] AC-C34: Idempotency — re-running on fully migrated board reports `Migrated: 0`
- [ ] AC-C35: Idempotency checks follow lane-specific rules (contract-critical archive fields, canonical active-task fields). **Branch matrix:** archive files with invalid `archival_refs` (non-list or list containing booleans) must NOT be treated as already migrated — must return `"failed"` with manual-action reason (§5.3 Lane B point 3, `migrate.py:267-268`)
- [ ] AC-C36: `--dry-run` writes nothing; only prints actions
- [ ] AC-C37: Crash mid-migration leaves no partial files (uses atomic_write); resume converges
- [ ] AC-C38: Exit code 1 if any file failed; 0 otherwise
- [ ] AC-C38a: When `config`/`archive` lanes leave unresolved manual work, emit manual-action summary for `type:user-action` tasks. **Branch matrix:** archive lane failures for BOTH invalid `archival_reason` AND invalid `archival_refs` must each produce entries in `MANUAL ACTION SUMMARY:` on stderr (`migrate.py:450-451` → `:506`)
- [ ] All RED tests from C-07 (#1052) pass
[[2026-04-23]]
## Test-Writer Notes
- Non-standard pass-through: implementation and tests were both delivered under C-07 (#1052) in the same builder cycle.
- Test file: `serve/kanban/tests/test_migrate.py` (57 tests — all PASS)
- AC coverage: AC-C31 through AC-C38a fully covered (see TestFromAC_MigrateEntryPoint, TestFromAC_LaneSelection, TestFromAC_LaneAlgorithms, TestFromAC_Idempotency, TestFromAC_DryRun, TestFromAC_CrashRecovery, TestFromAC_ExitCode, TestFromAC_LaneSelectionStrict, TestFromAC_ArchiveLaneAlgorithmsStrict, TestFromAC_IdempotencyEdgeCases, TestFromAC_DryRunStrict, TestFromAC_CrashRecoverySubprocess, TestFromAC_ManualActionSummaryStrict)
- `migrate.py` commits: 5 builder commits all tagged #1052 — implementation predates #1061 dispatch.
- No task-scoped `tests/test_migrate_1061.py` created: all AC lines produce passing tests against the existing implementation; writing artificial failing tests would be misleading.
- Builder for #1061: run `uv run pytest serve/kanban/tests/test_migrate.py -q` to confirm all 57 pass, then advance to review.
[[2026-04-23]]
## Builder Notes
- Implementation: no code changes in this cycle; existing `serve/kanban/src/owlbear_kanban/migrate.py` implementation satisfies AC-C31 through AC-C38a.
- Verification: delegated scoped GREEN check via quality-runner for `serve/kanban/tests/test_migrate.py`.
- Tests: 57 passed, 0 failed (task-scoped migrate suite).
- Lint: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- Coverage: attempted during scoped run; pytest-cov measurement artifact reported under worker interaction, but full task-scoped suite executed and passed.
- Evidence summary: lane selection, per-lane algorithm behavior, idempotency, dry-run semantics, crash recovery, exit codes, and manual-action summaries are validated by passing AC-mapped `TestFromAC_*` coverage in `test_migrate.py`.

Post-task reflection:
- Problem faced: this task arrived as a non-standard pass-through where implementation pre-existed from #1052.
- Workaround applied: treated #1061 as evidence/verification gate and validated with scoped quality-runner execution only.
- Pattern discovered: pass-through GREEN tasks benefit from explicit test-writer provenance notes to avoid duplicate edits.
- Time sink: coverage reporting instability in scoped worker mode can obscure otherwise-green verification.
- Quality gap: none in implementation surfaced; only measurement tooling artifact remains.
[[2026-04-23]]
## Review Evidence
### Test Results
- pytest: 57 passed, 0 failed (`serve/kanban/tests/test_migrate.py` via quality-runner)

### Lint
- ruff: clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence. The suite exercises the CLI through subprocess invocation, so pytest-cov reported `No data was collected`. Functional evidence came from the passing AC suite, not coverage percentage.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C31 | `serve/kanban/tests/test_migrate.py:193`, `:202` | Yes | COVERED |
| AC-C32 | `serve/kanban/tests/test_migrate.py:215`, `:613` | Yes | COVERED |
| AC-C33 | `serve/kanban/tests/test_migrate.py:279`, `:725` | Yes | COVERED |
| AC-C34 | `serve/kanban/tests/test_migrate.py:404` | Yes | COVERED |
| AC-C35 | `serve/kanban/tests/test_migrate.py:794`, `:859` | No for the missing-`created` / missing-`updated` task path; current suite would not fail on that branch | MISSING |
| AC-C36 | `serve/kanban/tests/test_migrate.py:438`, `:928` | Yes | COVERED |
| AC-C37 | `serve/kanban/tests/test_migrate.py:961` | Yes | COVERED |
| AC-C38 | `serve/kanban/tests/test_migrate.py:549` | Yes | COVERED |
| AC-C38a | `serve/kanban/tests/test_migrate.py:1066` | No for rerunning `--lane config` after config is already migrated but still contains unresolved stubs; summary emission is only tested on the migrated branch | MISSING |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run on `serve/kanban/tests/test_migrate.py` | Yes | COVERED |

#### Security Review
- No security issues found. YAML loads use the safe loader path and writes go through `atomic_write`; no shell, eval, secret, or network surface was added.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected in the current suite. No `skip` / `xfail` substitutions found.

#### Test Quality
- One non-blocking quality deduction: `serve/kanban/tests/test_migrate.py:505` patches `os.replace`, but `_run_migrate()` launches the system under test in a subprocess at `serve/kanban/tests/test_migrate.py:170`, so that patch does not exercise the child process. The later subprocess-based crash-recovery tests at `serve/kanban/tests/test_migrate.py:961` provide the real AC-C37 proof.

#### Data Safety
- No additional data-safety findings. Task, archive, and config writes use `atomic_write` at `serve/kanban/src/owlbear_kanban/migrate.py:211`, `:281`, and `:372`.

#### Builder Process Quality
- CLEAN. One builder section in the task body; no retry-loop evidence.

### Failing Findings
1. AC-C38a implementation failure: rerunning `--lane config` on an already-migrated config with unresolved stub fields emits no manual-action summary.
   - `_migrate_config()` returns `"already"` at `serve/kanban/src/owlbear_kanban/migrate.py:329` before any summary bookkeeping.
   - `_run_lane()` only appends config manual-action items when `result == "migrated" and not dry_run` at `serve/kanban/src/owlbear_kanban/migrate.py:442`.
   - `main()` emits `MANUAL ACTION SUMMARY:` only when `manual_actions` is non-empty at `serve/kanban/src/owlbear_kanban/migrate.py:506`.
   - Existing tests split the proof across separate branches: `serve/kanban/tests/test_migrate.py:859` covers the `already` path, and `serve/kanban/tests/test_migrate.py:1066` covers summary emission, but no test covers the combination required by AC-C38a.
2. AC-C35 implementation failure: `_is_task_migrated()` can classify a task missing `created` or `updated` as already migrated.
   - `_is_task_migrated()` starts at `serve/kanban/src/owlbear_kanban/migrate.py:121`.
   - Timestamp validation uses `fm.get(field)` at `serve/kanban/src/owlbear_kanban/migrate.py:126`; missing fields therefore flow through `_is_timestamp_utc_plus_00(None)` as acceptable.
   - Only `_ACTIVE_TASK_DEFAULTS` fields are presence-checked, so a task missing canonical timestamp fields can still be treated as `already`.
   - The only AC-C35 task-edge proof in the suite is `serve/kanban/tests/test_migrate.py:794`, which covers missing `archival_refs`, not missing `created` / `updated`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:9`; `serve/kanban/tests/test_migrate.py:193` | `TestFromAC_MigrateEntryPoint` | PASS |
| AC-C32 | lane dispatch and summary behavior exercised by `serve/kanban/tests/test_migrate.py:215` and `:613` | `TestFromAC_LaneSelection`, `TestFromAC_LaneSelectionStrict` | PASS |
| AC-C33 | task/archive/config transformation checks at `serve/kanban/tests/test_migrate.py:279` and `:725` | `TestFromAC_LaneAlgorithms`, `TestFromAC_ArchiveLaneAlgorithmsStrict` | PASS |
| AC-C34 | rerun `Migrated: 0` assertions at `serve/kanban/tests/test_migrate.py:404` | `TestFromAC_Idempotency` | PASS |
| AC-C35 | idempotency code at `serve/kanban/src/owlbear_kanban/migrate.py:121` and `:329`; tests miss missing-timestamp task branch | `TestFromAC_IdempotencyEdgeCases` | FAIL |
| AC-C36 | dry-run assertions at `serve/kanban/tests/test_migrate.py:438` and `:928` | `TestFromAC_DryRun`, `TestFromAC_DryRunStrict` | PASS |
| AC-C37 | subprocess crash/resume proof at `serve/kanban/tests/test_migrate.py:961` | `TestFromAC_CrashRecoverySubprocess` | PASS |
| AC-C38 | exit-code and stderr failure assertions at `serve/kanban/tests/test_migrate.py:549` | `TestFromAC_ExitCode` | PASS |
| AC-C38a | manual-action summary emission is branch-incomplete versus code at `serve/kanban/src/owlbear_kanban/migrate.py:442` and `:506` | `TestFromAC_ManualActionSummaryStrict` | FAIL |
| All RED tests from C-07 (#1052) pass | quality-runner: 57 passed, 0 failed | `serve/kanban/tests/test_migrate.py` | PASS |

### Deductions
- -0.14: AC-C38a missing on config rerun through the `already` branch.
- -0.08: AC-C35 task idempotency predicate accepts missing canonical timestamps.
- -0.04: one crash-recovery test is ineffective across the subprocess seam.

### Verdict
- FAIL -> in-progress
- Confidence: 0.74

### Action
- Fix config-lane manual-action summary emission so unresolved stub fields are still surfaced when `_migrate_config()` returns `already`.
- Tighten `_is_task_migrated()` so `created` and `updated` must be present and normalised before the file is treated as already migrated.
- Add AC-scoped tests for both branches above.

### Reflection
- Pass-through GREEN tasks still require full implementation review; a green inherited suite is not sufficient evidence by itself.
- Idempotent migrations can still have unresolved user-action obligations; `migrated` versus `already` must be tested explicitly.
- CLI subprocess suites are good boundary proof but can hide ineffective monkeypatch-based tests and defeat coverage instrumentation.
[[2026-04-23]]
## Builder Notes
- Implementation: updated `serve/kanban/src/owlbear_kanban/migrate.py`.
- Fixes applied:
- AC-C35: tightened `_is_task_migrated()` so `created` and `updated` must be present before a task can be classified as `already` migrated.
- AC-C38a: added config stub detection (`agent_map`, `agent_types`, `agent_compatibility`) and now emit config manual-action summary on both `migrated` and `already` config-lane runs when unresolved stubs remain.
- Tests: 57 passed, 0 failed (`serve/kanban/tests/test_migrate.py`).
- Lint: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- Coverage: pytest-cov reported `No data was collected` in scoped worker execution; functional AC evidence remains the passing migrate suite.
- Evidence summary: lane handling and exit-code behavior unchanged; idempotency predicate for active tasks no longer accepts missing canonical timestamps; config reruns now continue surfacing unresolved manual follow-up obligations as required.

Post-task reflection:
- Problem faced: previous AC gaps were on under-covered branches, so baseline suite stayed green despite contract drift.
- Workaround applied: implemented branch-tightening fixes directly in migration predicates/summary routing without changing test assets.
- Pattern discovered: idempotency guards must validate field presence first, then normalization shape.
- Time sink: coverage instrumentation in scoped worker mode remained unstable (`no-data-collected`) despite successful execution.
- Quality gap: no remaining implementation gaps identified in the touched path.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 57 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence. The suite invokes the CLI through subprocesses, so pytest-cov returned `no-data-collected`. This is not treated as a separate failure, but it means AC proof must come from explicit assertions.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC-C31 | `serve/kanban/pyproject.toml:8-9` is correct, but `serve/kanban/tests/test_migrate.py:196-200` only checks substring presence and `:202-207` exercises module invocation rather than the named console script. | LAX |
| AC-C32 | Dispatch logic in `serve/kanban/src/owlbear_kanban/migrate.py:458-470` is present, but `serve/kanban/tests/test_migrate.py:218-270` and `:616-653` do not prove the all-lane path processed all three lanes. | LAX |
| AC-C33 | Representative task, archive, and config mutations are asserted at `serve/kanban/tests/test_migrate.py:282-348`, `:365-396`, and `:728-779`. | COVERED |
| AC-C34 | `serve/kanban/tests/test_migrate.py:407-430` pins `Migrated: 0`. | COVERED |
| AC-C35 | Builder code in `serve/kanban/src/owlbear_kanban/migrate.py:123-136` now matches Brief C task-idempotency rules in `.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:473-486`, but no `TestFromAC_*` case asserts that a task missing `created` or `updated` is migrated rather than skipped. Existing task-side proofs at `serve/kanban/tests/test_migrate.py:355-362` and `:794-821` do not cover that branch. | MISSING |
| AC-C36 | `serve/kanban/tests/test_migrate.py:441-492` and `:928-953` pin no-write behavior. | COVERED |
| AC-C37 | `serve/kanban/tests/test_migrate.py:961-1054` proves crash and resume behavior at the subprocess seam. | COVERED |
| AC-C38 | `serve/kanban/tests/test_migrate.py:552-593` pins success and failure exit codes plus FAIL stderr lines. | COVERED |
| AC-C38a | Builder code in `serve/kanban/src/owlbear_kanban/migrate.py:476-480` and `:542-547` now emits config manual-action summaries on both `migrated` and `already` paths, but `serve/kanban/tests/test_migrate.py:1066-1100` covers only the initial config migration path and `:1102-1131` covers archive failure. No `TestFromAC_*` case proves a config-lane rerun on an already-migrated config with unresolved stubs still emits the summary. | MISSING |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run on `serve/kanban/tests/test_migrate.py`. | COVERED |

#### Security Review
- No security issues found in the reviewed scope. Writes still go through `atomic_write`, and no shell, network, or eval surface was introduced.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected. The reviewed retry changed `serve/kanban/src/owlbear_kanban/migrate.py`, not the AC test file.

#### Test Quality
- WEAK assertion specificity: `serve/kanban/tests/test_migrate.py:196-200` only checks the string `kanban-migrate`; `:599-605` accepts broad manual-action wording.
- WEAK mutation resistance: removing the config branch from `serve/kanban/src/owlbear_kanban/migrate.py:470` would not be caught by the current all-lane tests at `serve/kanban/tests/test_migrate.py:256-270` and `:634-644`.
- One ineffective crash test remains at `serve/kanban/tests/test_migrate.py:505-527` because `_run_migrate()` launches the SUT in a subprocess at `serve/kanban/tests/test_migrate.py:170-185`. The later subprocess crash suite provides the real AC-C37 proof.

#### Data Safety
- No data-safety issues found. Task, archive, and config writes still use `atomic_write` at `serve/kanban/src/owlbear_kanban/migrate.py:216`, `:286`, and `:406`.

#### Builder Process Quality
- CLEAN. Two builder sections are present in the task body, with one substantive retry and a changed approach after the prior review.

### Failing Findings
1. Test gap: AC-C35 proof remains incomplete after the implementation fix. Brief C requires task idempotency to reject files missing canonical timestamp fields (`.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:473-486`, `:716-721`), but no AC-scoped test exercises the missing-`created` or missing-`updated` path. Existing task-side coverage is limited to an exact modern exemplar and missing `archival_refs` at `serve/kanban/tests/test_migrate.py:355-362` and `:794-821`.
2. Test gap: AC-C38a proof remains incomplete after the implementation fix. The code now records config manual actions on both result paths at `serve/kanban/src/owlbear_kanban/migrate.py:476-480`, but the suite never reruns the config lane against an already-migrated config with unresolved stubs. The config summary tests at `serve/kanban/tests/test_migrate.py:1066-1100` only cover the initial migration path.
3. Test quality failure: AC-C31 and AC-C32 assertions are too weak to guard the contract. `serve/kanban/tests/test_migrate.py:196-200` does not verify the actual `[project.scripts]` mapping in `serve/kanban/pyproject.toml:8-9`, and the all-lane tests at `serve/kanban/tests/test_migrate.py:256-270` and `:634-644` do not prove task, archive, and config processing all happened.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:8-9` is correct; proof in `serve/kanban/tests/test_migrate.py:196-207` is lax. | FAIL |
| AC-C32 | Implementation path exists at `serve/kanban/src/owlbear_kanban/migrate.py:458-470`; all-lane proof in `serve/kanban/tests/test_migrate.py:218-270` and `:616-653` is incomplete. | FAIL |
| AC-C33 | Mutation checks at `serve/kanban/tests/test_migrate.py:282-396` and `:728-779`. | PASS |
| AC-C34 | Idempotency counts pinned at `serve/kanban/tests/test_migrate.py:407-430`. | PASS |
| AC-C35 | Implementation aligns with Brief C, but AC proof is missing for the missing-timestamp task branch. | FAIL |
| AC-C36 | No-write assertions at `serve/kanban/tests/test_migrate.py:441-492` and `:928-953`. | PASS |
| AC-C37 | Subprocess crash-resume proof at `serve/kanban/tests/test_migrate.py:961-1054`. | PASS |
| AC-C38 | Exit-code and stderr checks at `serve/kanban/tests/test_migrate.py:552-593`. | PASS |
| AC-C38a | Implementation aligns with the required config summary behavior, but AC proof is missing for the already-migrated config rerun branch. | FAIL |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run. | PASS |

### Deductions
- -0.07: AC-C35 branch-specific proof still missing after the builder fix.
- -0.07: AC-C38a branch-specific proof still missing after the builder fix.
- -0.04: AC-C31 proof is lax.
- -0.04: AC-C32 all-lane proof is lax.
- -0.02: one crash-recovery test remains ineffective across the subprocess seam.

### Verdict
- FAIL to todo
- Confidence: 0.86

### Action
- Add an AC-scoped task test proving files missing `created` or `updated` are migrated, not skipped.
- Add an AC-scoped config test proving a rerun on an already-migrated config with unresolved stubs still emits the full manual-action summary, including `type:user-action` guidance.
- Strengthen AC-C31 and AC-C32 assertions so they verify the exact console-script mapping and that the all-lane path processes task, archive, and config targets.
- No additional implementation defect is required to explain the current failure; this review is routing on proof quality.

### Reflection
- A builder retry can close the implementation defect while leaving the original AC-proof gap untouched.
- Brief authority matters when separating implementation defects from review-proof defects; stricter inferred invariants are not enough.
- Subprocess-driven CLI suites need especially explicit branch assertions because green counts and unavailable coverage can hide missing proof.
[[2026-04-23]]
## Test-Writer Notes
- Retry cycle: reviewer cited 4 missing-proof gaps. Added 6 new `TestFromAC_*` tests; all PASS (implementation was already correct — these are proof-strengthening tests per reviewer directive "routing on proof quality").
- Test file: `serve/kanban/tests/test_migrate.py` (63 tests total, 0 failed)
- Commit: `52594ffe` — "test: add AC proof tests for C31/C32/C35/C38a gaps (#1061, test-writer)"

### New tests added (6)

| New Test | AC Gap Addressed |
|----------|-----------------|
| `TestFromAC_MigrateEntryPoint::test_ac_c31_pyproject_scripts_exact_key_value` | AC-C31 — verifies exact `kanban-migrate = "owlbear_kanban.migrate:main"` key-value in `[project.scripts]` |
| `TestFromAC_LaneSelection::test_ac_c32_all_lane_processes_task_archive_and_config_content` | AC-C32 — asserts task (`claimed_by` removed), archive (`archival_reason:` added), AND config (`name: research` gone, `- research` present) all mutated by `--lane all` |
| `TestFromAC_IdempotencyEdgeCases::test_ac_c35_task_missing_created_is_migrated_not_skipped` | AC-C35 — task without `created` → `Migrated: 1` (not `Already: 1`) |
| `TestFromAC_IdempotencyEdgeCases::test_ac_c35_task_missing_updated_is_migrated_not_skipped` | AC-C35 — task without `updated` → `Migrated: 1` |
| `TestFromAC_ManualActionSummaryStrict::test_ac_c38a_config_rerun_already_migrated_with_empty_stubs_emits_summary` | AC-C38a — `--lane config` rerun on already-migrated config with `agent_map: {}` stubs → `MANUAL ACTION SUMMARY:` on stderr |
| `TestFromAC_ManualActionSummaryStrict::test_ac_c38a_config_rerun_summary_mentions_stub_fields` | AC-C38a — rerun summary names `agent_map`, `agent_types`, `agent_compatibility` |

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (strict pyproject key-value added) |
| AC-C32 | COVERED (all-lane content proof added) |
| AC-C33 | COVERED (unchanged) |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED (missing `created`/`updated` branches now proved) |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED (config rerun `already`-path summary branch now proved) |

### Execution

- pytest: 63 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean
- All 6 new tests pass because the builder's implementation is already correct; these tests prove the specific branches the reviewer required.
[[2026-04-23]]
## Builder Notes
- Implementation: no code changes in this cycle (verification-only close).
- Verification method: delegated scoped run to `quality-runner` per pipeline mandate.
- Tests: `serve/kanban/tests/test_migrate.py` -> 63 passed, 0 failed, 0 skipped.
- Lint: `uv run ruff check serve/kanban/src/owlbear_kanban/migrate.py serve/kanban/tests/test_migrate.py` -> clean.
- Coverage: not re-measured in this scoped close; AC proof relies on passing `TestFromAC_*` coverage already present in the migrate suite.
- Evidence summary: AC-C31 through AC-C38a remain satisfied by passing strict proof tests, including the added AC-C31/32/35/38a branch-strengthening cases.

Post-task reflection:
- Problem faced: task reached builder as a late-cycle verification gate rather than a fresh implementation step.
- Workaround applied: used strict scoped quality-runner verification only, with zero incidental edits.
- Pattern discovered: proof-strengthening retries can end with a clean no-diff builder close when test-writer already sealed branch gaps.
- Time sink: none in this cycle.
- Quality gap: none observed in scoped migrate implementation/test slice.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 63 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence because the CLI tests execute `python -m owlbear_kanban.migrate` in a subprocess. This was not treated as a separate failure.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C31 | `test_ac_c31_pyproject_scripts_exact_key_value` | Yes | COVERED |
| AC-C32 | `TestFromAC_LaneSelection`, `TestFromAC_LaneSelectionStrict` | Yes for the exercised tasks/all-lane behavior; archive->config and config->archive exclusivity are only partially pinned | LAX |
| AC-C33 | `TestFromAC_LaneAlgorithms`, `TestFromAC_ArchiveLaneAlgorithmsStrict` | Yes for the exercised task/archive/config branches | COVERED |
| AC-C34 | `test_ac_c34_*` | Yes | COVERED |
| AC-C35 | `TestFromAC_IdempotencyEdgeCases` | No for the archive invalid `archival_refs` branch at `serve/kanban/src/owlbear_kanban/migrate.py:267-268` | MISSING |
| AC-C36 | `TestFromAC_DryRun*` | Yes | COVERED |
| AC-C37 | `TestFromAC_CrashRecoverySubprocess` | Yes for crash+resume; the parent-process `os.replace` patch test is not relied on | COVERED |
| AC-C38 | `TestFromAC_ExitCode` | Yes | COVERED |
| AC-C38a | `TestFromAC_ManualActionSummaryStrict` | No for the archive invalid `archival_refs` summary path via `serve/kanban/src/owlbear_kanban/migrate.py:450-451` | MISSING |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run | Yes | COVERED |

#### Security Review
- No issues found. YAML uses safe/round-trip loaders; writes still go through `atomic_write`; no shell, network, or eval surface was added.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected. This retry added tests only.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact script-mapping and summary-header assertions are present. |
| Negative/error-path coverage | WEAK | No AC-scoped archive invalid `archival_refs` tests exist for idempotency or manual-action behavior. |
| Manual mutation reasoning | ADEQUATE | Main lane/config/task branches are pinned, but a regression on invalid `archival_refs` would still pass. |
| Test independence | STRONG | Each case builds a fresh board under `tmp_path`. |
| Descriptive names | STRONG | AC-tagged names are used throughout the suite. |

#### Data Safety
- No implementation data-safety issues found. Non-dry-run writes still use `atomic_write` on task, archive, and config paths.

#### Implementation-Aware Gaps
- `_migrate_archive_file()` has a distinct invalid `archival_refs` failure branch at `serve/kanban/src/owlbear_kanban/migrate.py:267-268`.
- `_run_lane()` converts archive manual-action failures into summary items at `serve/kanban/src/owlbear_kanban/migrate.py:450-451`.
- The AC-scoped suite covers invalid reason (`serve/kanban/tests/test_migrate.py:863`, `:1203`, `:1217`) and valid integer refs (`:876`) but no invalid `archival_refs` path.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 3 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- `serve/kanban/tests/test_migrate.py:540-558` patches `os.replace` in the parent process while `_run_migrate()` launches the SUT in a subprocess at `:170-185`; that specific test is ineffective. I did not gate on it because Brief C §3.2 already allows `.tmp-*` siblings on a true mid-write crash, and `serve/kanban/tests/test_storage_io.py:196-205` already carries direct `atomic_write` cleanup proof.

### Failing Findings
1. AC-C35 proof gap: archive idempotency rules are still missing an AC-scoped negative test for invalid `archival_refs`. The production branch exists at `serve/kanban/src/owlbear_kanban/migrate.py:267-268`, but `TestFromAC_IdempotencyEdgeCases` only covers invalid reason and valid integer refs at `serve/kanban/tests/test_migrate.py:863` and `:876`.
2. AC-C38a proof gap: archive manual-action summary coverage is still missing the invalid `archival_refs` variant. Summary collation happens at `serve/kanban/src/owlbear_kanban/migrate.py:450-451`, but `TestFromAC_ManualActionSummaryStrict` only proves the invalid reason path at `serve/kanban/tests/test_migrate.py:1203` and `:1217`.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:8-9`; `serve/kanban/tests/test_migrate.py:209-215` exact mapping assertion | PASS |
| AC-C32 | `serve/kanban/src/owlbear_kanban/migrate.py:458-476`; lane-selection tests exercise tasks/archive/config/all paths | PASS |
| AC-C33 | `serve/kanban/tests/test_migrate.py:317-423`, `:760-814` cover task/archive/config algorithm branches | PASS |
| AC-C34 | `serve/kanban/tests/test_migrate.py:442-467` pins `Migrated: 0` on rerun and modern-board inputs | PASS |
| AC-C35 | Missing AC-scoped proof for the archive invalid `archival_refs` branch at `serve/kanban/src/owlbear_kanban/migrate.py:267-268` | FAIL |
| AC-C36 | `serve/kanban/tests/test_migrate.py:476-522`, `:1029-1054` prove dry-run immutability and summary output | PASS |
| AC-C37 | `serve/kanban/tests/test_migrate.py:1062-1158` proves crash+resume convergence at the subprocess seam | PASS |
| AC-C38 | `serve/kanban/tests/test_migrate.py:584-644` pins exit codes and FAIL stderr lines | PASS |
| AC-C38a | Config summary and archive invalid-reason summary are covered, but archive invalid `archival_refs` summary is unproved | FAIL |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run: 63 passed, 0 failed | PASS |

### Deductions
- -0.07: AC-C35 archive invalid `archival_refs` branch still unproved in `TestFromAC_*`.
- -0.05: AC-C38a archive invalid `archival_refs` manual-action summary path still unproved.

### Confidence: 0.88
### Verdict: FAIL -> backlog
### Action
- Add a `TestFromAC_IdempotencyEdgeCases` case proving archive files with invalid `archival_refs` are not treated as already migrated and return manual-action failure.
- Add a `TestFromAC_ManualActionSummaryStrict` case proving the same invalid `archival_refs` archive path emits `MANUAL ACTION SUMMARY:` on stderr.
- Loop-breaker routing applies here: the task body already contained two prior `## Review Evidence` FAIL sections, so this third review failure goes to `backlog` per protocol.

### Reflection
- A narrow remaining branch gap can survive multiple otherwise-green retries when the suite only proves one variant of a two-field contract.
- The subprocess coverage artifact remained non-blocking; the real issue was branch-specific proof, not execution quality.
- Brief language around crash semantics mattered: `atomic_write` cleanup tests belong to the primitive, while the migration AC focuses on crash/resume behavior.
- No implementation defect was found in the current code path; this rejection is on AC-proof completeness.
[[2026-04-23]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration entry point, one domain |
| Interface clarity | REFINE | AC-C35 and AC-C38a missing explicit branch-matrix requirements for `archival_refs` — root cause of 3-cycle loop |
| Dependency correctness | PASS | #1052 and #1059 both archived/done |
| Module layering | PASS | `migrate.py` imports from `storage_io` and `body_parser` only — no upward imports |
| TDD compliance | PASS | Tagged `tdd:green`, test suite exists from #1052 (63 tests, all pass) |
| KISS/YAGNI | PASS | Minimal scope — migration script only |
| Premise challenge | PASS | Migration script required for Brief C schema cutover |
| Pattern consistency | PASS | Uses `atomic_write`, `ruamel.yaml`, `argparse` — consistent with codebase patterns |
| Security surface | PASS | YAML safe loader, atomic writes, no shell/eval/network surface |
| Single domain | PASS | Kanban domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|--------------|-----------|----------|-------------|
| `_migrate_archive_file` L265-266 | Invalid `archival_reason` | None (returns "failed") | Yes | FAIL line + manual-action summary |
| `_migrate_archive_file` L267-268 | Invalid `archival_refs` | None (returns "failed") | Yes | FAIL line + manual-action summary |
| `_migrate_task_file` | Missing `created`/`updated` | None (returns "migrated") | Yes | Re-migrated with defaults |

### Challenge Results
- Challenger: reconsider (0.47)
- Key challenge: Brief C §5.3 already names both archive fields; AC wording alone won't guarantee branch coverage; the reviewer's exact instructions were already missed twice
- Architect response: ACCEPTED IN PART — the challenger is correct that simply naming fields is insufficient. However, the refinement goes beyond naming: it adds **explicit test scenarios** (invalid `archival_refs` archive branch) as sub-points in AC-C35 and AC-C38a, plus a loop-breaker guidance section with the exact 2 missing tests. This is materially different from what the test-writer received previously (reviewer action items buried in review cycle notes). The implementation is correct at `migrate.py:267-268` and `:450-451` — the gap is proof only.

### AC Refinement Applied
AC-C35 and AC-C38a refined to include explicit branch-matrix requirements:

**AC-C35** (revised): Idempotency checks follow lane-specific rules (contract-critical archive fields, canonical active-task fields). **Branch matrix:** archive files with invalid `archival_refs` (non-list or list containing booleans) must NOT be treated as already migrated — they must return `"failed"` with manual-action reason. Test must exercise `_migrate_archive_file` at `migrate.py:267-268`.

**AC-C38a** (revised): When `config`/`archive` lanes leave unresolved manual work, emit manual-action summary for `type:user-action` tasks. **Branch matrix:** archive lane failures for BOTH invalid `archival_reason` AND invalid `archival_refs` must each produce entries in `MANUAL ACTION SUMMARY:` on stderr. Test must exercise the `archival_refs` variant at `migrate.py:450-451` feeding into `main()` summary at `:506`.

### Loop-Breaker Guidance
This task returns from 3rd review FAIL. The implementation is correct. Exactly 2 tests are missing:
1. `TestFromAC_IdempotencyEdgeCases::test_ac_c35_archive_invalid_archival_refs_not_treated_as_already` — archive file with invalid `archival_refs` (e.g. `archival_refs: "not-a-list"`) must produce `Migrated: 0`, `Failed: 1`, exit code 1, and `manual-action required: invalid archival_refs` on stderr.
2. `TestFromAC_ManualActionSummaryStrict::test_ac_c38a_archive_invalid_refs_emits_manual_action_summary` — same invalid `archival_refs` archive file must produce `MANUAL ACTION SUMMARY:` on stderr with the archive path.

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC-C35 and AC-C38a with explicit branch-matrix requirements and loop-breaker guidance. Advanced to todo.
[[2026-04-23]]
## Test-Writer Notes
- Retry cycle: reviewer cited 2 missing branch-proof gaps (archival_refs variants for AC-C35 and AC-C38a).
- Test file: `serve/kanban/tests/test_migrate.py` (65 tests total, 0 failed)
- Commit: `51050b54` — "test: add AC proof tests for C35/C38a archival_refs branch (#1061, test-writer)"

### New tests added (2)

| New Test | AC Gap Addressed |
|----------|-----------------|
| `TestFromAC_IdempotencyEdgeCases::test_ac_c35_archive_invalid_archival_refs_not_treated_as_already` | AC-C35 branch matrix — archive with `archival_refs: "not-a-list"` must return `Failed: 1`, `Migrated: 0`, exit 1, `manual-action required: invalid archival_refs` on stderr |
| `TestFromAC_ManualActionSummaryStrict::test_ac_c38a_archive_invalid_refs_emits_manual_action_summary` | AC-C38a branch matrix — same invalid-refs archive must produce `MANUAL ACTION SUMMARY:` on stderr with the archive path |

Also added `_ARCHIVE_INVALID_REFS` fixture (`archival_refs: "not-a-list"`) to support both tests.

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (unchanged) |
| AC-C32 | COVERED (unchanged) |
| AC-C33 | COVERED (unchanged) |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED (invalid archival_refs branch now proved) |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED (invalid archival_refs summary branch now proved) |

### Execution
- pytest: 65 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean
- Both new tests pass because the implementation is already correct at `migrate.py:267-268` and `:450-451`; these tests prove the specific archival_refs branches the reviewer required.
[[2026-04-23]]
## Builder Notes
- Implementation: no code changes in this cycle. Existing `serve/kanban/src/owlbear_kanban/migrate.py` behavior matches AC-C31 through AC-C38a.
- Verification method: quality-runner scoped validation on `serve/kanban/tests/test_migrate.py`.
- Tests: 65 passed, 0 failed, 0 skipped.
- Lint: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- Coverage: `pytest-cov` reported no data collected for `owlbear_kanban.migrate` because the suite executes key paths in subprocesses; functional AC evidence is the full passing `TestFromAC_*` suite.
- Evidence summary: strict AC proof tests for archival_refs branch matrix (AC-C35 and AC-C38a) now pass along with lane-selection, idempotency, dry-run, crash-resume, and exit-code checks.

Post-task reflection:
- Problem faced: this task was a verification gate after multiple review loops rather than a fresh implementation step.
- Workaround applied: produced a fresh scoped quality-runner run in this builder cycle with no incidental edits.
- Pattern discovered: when implementation is stable, closing evidence gaps in `TestFromAC_*` can legitimately yield a no-diff builder close.
- Time sink: coverage instrumentation is limited for subprocess-heavy CLI tests.
- Quality gap: none observed in the scoped module and test slice.
[[2026-04-23]]
## Builder Notes
- Implementation: no code changes in this cycle; verification-only builder pass on existing migrate entry-point implementation.
- Verification: quality-runner scoped run executed for `serve/kanban/tests/test_migrate.py`.
- Tests: 65 passed, 0 failed, 0 skipped.
- Lint: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- Coverage: measurement artifact (`No data was collected`) for `owlbear_kanban.migrate` due subprocess/CLI execution path; functional AC evidence remains full passing TestFromAC suite.
- Evidence summary: AC-C31 through AC-C38a remain satisfied by passing strict migrate suite proofs, including archival_refs branch matrix checks.

Post-task reflection:
- Problem faced: task was already in `review`, so builder work here is verification-only.
- Workaround applied: reran independent scoped quality-runner evidence instead of attempting redundant code edits.
- Pattern discovered: subprocess-heavy CLI tests can preserve strong functional confidence while coverage instrumentation reports no-data.
- Time sink: none.
- Quality gap: none observed in scoped module/test slice.
[[2026-04-23]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 65 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence. The CLI suite executes `sys.executable -m owlbear_kanban.migrate` in subprocesses, so quality-runner reported coverage as N/A. Functional proof must therefore come from explicit AC assertions.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C31 | `TestFromAC_MigrateEntryPoint::test_ac_c31_pyproject_scripts_exact_key_value` | Yes | COVERED |
| AC-C32 | `test_ac_c32_lane_archive_runs_only_archive_lane`, `test_ac_c32_lane_config_runs_only_config_lane`, `test_ac_c32_single_lane_does_not_touch_other_dir`, `test_ac_c32_all_lane_processes_task_archive_and_config_content` | No for archive lane accidentally mutating config, and no for config lane accidentally mutating archive | MISSING |
| AC-C33 | `TestFromAC_LaneAlgorithms`, `TestFromAC_ArchiveLaneAlgorithmsStrict` | Yes for the exercised task, archive, and config transformations | COVERED |
| AC-C34 | `TestFromAC_Idempotency` | Yes | COVERED |
| AC-C35 | `test_ac_c35_archive_invalid_archival_refs_not_treated_as_already` | Yes for the non-list invalid-refs case, no for the boolean-in-list invalid-refs case named in the task AC | MISSING |
| AC-C36 | `TestFromAC_DryRun`, `TestFromAC_DryRunStrict` | Yes | COVERED |
| AC-C37 | `TestFromAC_CrashRecoverySubprocess` | Yes | COVERED |
| AC-C38 | `TestFromAC_ExitCode` | Yes | COVERED |
| AC-C38a | `TestFromAC_ManualActionSummaryStrict` | Yes for config-stub summary and invalid-refs summary emission | COVERED |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run | Yes | COVERED |

#### Security Review
- No security issues found. No shell, network, eval, or secret surface was introduced.
- YAML parsing stays on the safe or round-trip loaders, and writes remain atomic at `serve/kanban/src/owlbear_kanban/migrate.py:216`, `:286`, and `:406`.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected in the current retry. The latest retry added tests at `serve/kanban/tests/test_migrate.py:1038` and `:1322`; it did not relax earlier checks.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact script-mapping and invalid-refs stderr assertions are present. |
| Negative/error-path coverage | WEAK | AC-C35 names invalid `archival_refs` as either non-list or list containing booleans, but the only invalid-refs fixture is `archival_refs: "not-a-list"` at `serve/kanban/tests/test_migrate.py:759`; no boolean-list case exists in the suite. |
| Manual mutation reasoning | WEAK | `serve/kanban/src/owlbear_kanban/migrate.py:464` and `:470` are separate archive/config lane branches, but the archive-lane proof at `serve/kanban/tests/test_migrate.py:242` and the config-lane proof at `:254` each assert only the task file stayed unchanged. A mutation that also ran config during archive lane, or archive during config lane, would still pass. |
| Test independence | STRONG | Each case builds a fresh board under `tmp_path`. |
| Descriptive names | STRONG | AC-tagged test names are used consistently. |

#### Data Safety
- No data-safety issues found. Non-dry-run task, archive, and config writes still go through `atomic_write` at `serve/kanban/src/owlbear_kanban/migrate.py:216`, `:286`, and `:406`.

#### Implementation-Aware Gaps
1. AC-C35 branch-matrix proof remains incomplete. The task AC requires invalid `archival_refs` cases for both non-list values and lists containing booleans. The implementation explicitly rejects booleans in `_is_archive_refs_valid` at `serve/kanban/src/owlbear_kanban/migrate.py:116`, but the only AC-scoped invalid-refs idempotency test uses the non-list fixture at `serve/kanban/tests/test_migrate.py:759` and `:1038`. No test exercises `[true]` or `[false]` in `archival_refs`, so a mutation removing the `not isinstance(item, bool)` guard would escape.
2. AC-C32 lane-exclusivity proof is still incomplete. The implementation branches archive and config independently at `serve/kanban/src/owlbear_kanban/migrate.py:464` and `:470`. The archive-lane test at `serve/kanban/tests/test_migrate.py:242-252` proves only that tasks stay unchanged; the config-lane test at `serve/kanban/tests/test_migrate.py:254-263` proves only that tasks stay unchanged. The tasks-only exclusivity test at `serve/kanban/tests/test_migrate.py:681` does not close those two missing directions.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 4 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The older parent-process `os.replace` patch test remains ineffective across the subprocess seam, but the subprocess crash-recovery suite carries the real AC-C37 proof, so I did not gate on that point.
- Coverage stayed unavailable for the known subprocess reason; this was not a separate failure.

### Failing Findings
1. AC-C35 proof gap: the refined task AC explicitly requires invalid `archival_refs` coverage for non-list values and boolean-containing lists, but the suite proves only the non-list variant. Evidence: `serve/kanban/src/owlbear_kanban/migrate.py:116`, `:267`; `serve/kanban/tests/test_migrate.py:759`, `:1038`; no boolean-based invalid-refs case exists in the test file.
2. AC-C32 proof gap: single-lane exclusivity is only partially proved. Evidence: `serve/kanban/src/owlbear_kanban/migrate.py:464`, `:470`; `serve/kanban/tests/test_migrate.py:242-252`, `:254-263`, `:681`, `:282`. Current tests would not fail if archive lane also migrated config or if config lane also migrated archive.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:9`; exact mapping asserted by `TestFromAC_MigrateEntryPoint::test_ac_c31_pyproject_scripts_exact_key_value` | PASS |
| AC-C32 | All-lane positive proof exists, but archive/config single-lane exclusivity is only partially pinned at `serve/kanban/tests/test_migrate.py:242-252`, `:254-263`, and `:681` | FAIL |
| AC-C33 | Task, archive, and config transformations are asserted by `TestFromAC_LaneAlgorithms` and `TestFromAC_ArchiveLaneAlgorithmsStrict` | PASS |
| AC-C34 | `TestFromAC_Idempotency` pins `Migrated: 0` on rerun | PASS |
| AC-C35 | Non-list invalid refs are proved, but boolean-containing list invalid refs from the task AC are not | FAIL |
| AC-C36 | `TestFromAC_DryRun` and `TestFromAC_DryRunStrict` prove no-write behavior | PASS |
| AC-C37 | `TestFromAC_CrashRecoverySubprocess` proves crash and resume convergence | PASS |
| AC-C38 | `TestFromAC_ExitCode` pins success/failure exit codes and FAIL stderr lines | PASS |
| AC-C38a | `TestFromAC_ManualActionSummaryStrict` proves config-stub summary and archive invalid-refs summary emission | PASS |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run: 65 passed, 0 failed | PASS |

### Deductions
- -0.08: AC-C35 boolean-list invalid-refs branch is unproved.
- -0.05: AC-C32 archive-lane exclusivity does not prove config remains untouched.
- -0.05: AC-C32 config-lane exclusivity does not prove archive remains untouched.

### Confidence: 0.82
### Verdict: FAIL
### Action
- Add an AC-scoped archive test where `archival_refs` is a list containing a boolean, and prove it fails with `manual-action required: invalid archival_refs` instead of being treated as already migrated.
- Add an AC-scoped archive-lane exclusivity test proving config content or mtime remains unchanged when only archive lane runs.
- Add an AC-scoped config-lane exclusivity test proving archive content or mtime remains unchanged when only config lane runs.
- No implementation defect is required to explain this rejection. The current code path looks correct; the failure is on proof completeness.
- Loop-breaker routing applies: the task body already contains three prior reviewer FAIL sections, so this fourth review rejection returns to backlog.

### Reflection
- Refined branch-matrix AC text has to be reviewed against the current task body, not against the last retry summary.
- A green subprocess CLI suite can still leave exact exclusivity and predicate sub-branches unproved.
- The safest place to stop another loop is the first review that sees the remaining proof hole, even when the implementation itself appears correct.
[[2026-04-23]]
## Architecture Review (cycle 2)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration entry point, one domain |
| Interface clarity | REFINE | AC-C32 exclusivity and AC-C35 boolean-list branch need explicit sub-bullets (root cause of 4-cycle loop) |
| Dependency correctness | PASS | #1052 and #1059 both archived |
| Module layering | PASS | `migrate.py` imports from `storage_io` and `body_parser` only |
| TDD compliance | PASS | 65 tests all pass, tagged `tdd:green` |
| KISS/YAGNI | PASS | Minimal scope — migration script only |
| Premise challenge | PASS | Migration script required for Brief C schema cutover |
| Pattern consistency | PASS | Uses `atomic_write`, `ruamel.yaml`, `argparse` — consistent |
| Security surface | PASS | YAML safe loader, atomic writes, no shell/eval/network |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.43)
- Key concerns: (1) previous loop-breaker guidance was incomplete — specified 2 tests, reviewer found 3 gaps including AC-C32 which wasn't in guidance; (2) AC text already named boolean-list variant but test-writer missed it
- Architect response: ACCEPTED — previous guidance was under-inclusive. This cycle provides exhaustive branch enumeration with completeness matrix. Implementation remains correct; all 4 review cycles confirmed proof-only gaps.

### AC Refinement Applied

**AC-C32** (revised): `--lane tasks|archive|config|all` runs only selected lane; `--lane all` runs all three. **Exclusivity proof required for all 6 cross-lane directions:**
  - (a) tasks→config: ✅ proved by `test_ac_c32_lane_tasks_runs_only_task_lane` (config mtime)
  - (b) tasks→archive: ✅ proved by `test_ac_c32_single_lane_does_not_touch_other_dir` (archive content)
  - (c) archive→tasks: ✅ proved by `test_ac_c32_lane_archive_runs_only_archive_lane` (task mtime)
  - (d) archive→config: ❌ MISSING — add test proving config content/mtime unchanged when `--lane archive` runs
  - (e) config→tasks: ✅ proved by `test_ac_c32_lane_config_runs_only_config_lane` (task mtime)
  - (f) config→archive: ❌ MISSING — add test proving archive content/mtime unchanged when `--lane config` runs

**AC-C35** (revised): Idempotency checks follow lane-specific rules. **Branch matrix for invalid `archival_refs`:**
  - (a) Non-list string (e.g. `"not-a-list"`): ✅ proved by `test_ac_c35_archive_invalid_archival_refs_not_treated_as_already`
  - (b) List containing boolean (e.g. `[true]`): ❌ MISSING — add test proving `archival_refs: [true]` returns `Failed: 1`, `Migrated: 0`, exit 1, `manual-action required: invalid archival_refs` on stderr

### Loop-Breaker Guidance (5th cycle — FINAL)

This task has cycled 4 times on proof-only gaps. Implementation is correct (confirmed by 4 independent reviews). Exactly 3 tests are missing. The test-writer MUST add all 3 and ONLY these 3:

**Test 1** — `TestFromAC_LaneSelection::test_ac_c32_archive_lane_does_not_touch_config`
```
Setup: _make_legacy_board + write legacy archive file; record config.yml mtime before
Action: _run_migrate(kanban_dir, lane="archive")
Assert: config.yml mtime unchanged AND config.yml content unchanged
```

**Test 2** — `TestFromAC_LaneSelection::test_ac_c32_config_lane_does_not_touch_archive`
```
Setup: _make_legacy_board + write legacy archive file; record archive file mtime and content before
Action: _run_migrate(kanban_dir, lane="config")
Assert: archive file mtime unchanged AND archive content unchanged
```

**Test 3** — `TestFromAC_IdempotencyEdgeCases::test_ac_c35_archive_boolean_list_refs_not_treated_as_already`
```
Fixture: archive file with `archival_refs: [true]` (a list containing a boolean)
Action: _run_migrate(kanban_dir, lane="archive")
Assert: exit code 1, stderr contains "manual-action required: invalid archival_refs", stdout contains "Failed: 1" and "Migrated: 0"
```

### Completeness Matrix (for test-writer verification)

After adding the 3 tests above, ALL cross-lane exclusivity directions are covered:

| Lane | Tasks | Archive | Config |
|------|-------|---------|--------|
| tasks | — | ✅ (existing) | ✅ (existing) |
| archive | ✅ (existing) | — | ✅ (Test 1) |
| config | ✅ (existing) | ✅ (Test 2) | — |

And both AC-C35 invalid refs variants are covered:

| Variant | Test |
|---------|------|
| Non-list string | ✅ (existing) |
| Boolean-containing list | ✅ (Test 3) |

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC-C32 with exhaustive 6-direction exclusivity sub-bullets and AC-C35 with explicit 2-variant branch matrix. Added loop-breaker guidance with exact test specifications, fixtures, and assertions for all 3 remaining gaps. Advanced to todo.
[[2026-04-23]]
## Test-Writer Notes
- Retry cycle: reviewer cited 3 missing proof gaps (AC-C32 archive→config and config→archive exclusivity; AC-C35 boolean-list refs branch).
- Test file: `serve/kanban/tests/test_migrate.py` (68 tests total, 0 failed)
- Commit: `892d95bd` — "test: add AC proof tests for C32 exclusivity and C35 boolean-refs branch (#1061, test-writer)"

### New tests added (3)

| New Test | AC Gap Addressed |
|----------|-----------------|
| `TestFromAC_LaneSelection::test_ac_c32_archive_lane_does_not_touch_config` | AC-C32 exclusivity (d) — `--lane archive` leaves config.yml mtime and content unchanged |
| `TestFromAC_LaneSelection::test_ac_c32_config_lane_does_not_touch_archive` | AC-C32 exclusivity (f) — `--lane config` leaves archive file mtime and content unchanged |
| `TestFromAC_IdempotencyEdgeCases::test_ac_c35_archive_boolean_list_refs_not_treated_as_already` | AC-C35 branch matrix (b) — `archival_refs: [true]` exits 1, `Failed: 1`, `Migrated: 0`, `manual-action required: invalid archival_refs` on stderr |

Also added `_ARCHIVE_BOOL_REFS` fixture (archive file with `archival_refs: [true]`) to support Test 3.

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (unchanged) |
| AC-C32 | COVERED (all 6 cross-lane exclusivity directions now proved) |
| AC-C33 | COVERED (unchanged) |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED (both invalid refs variants proved: non-list string and boolean-containing list) |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED (unchanged) |

### Execution
- pytest: 68 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean
- All 3 new tests pass because the implementation is already correct; these tests prove the specific branches required by the architect loop-breaker guidance.