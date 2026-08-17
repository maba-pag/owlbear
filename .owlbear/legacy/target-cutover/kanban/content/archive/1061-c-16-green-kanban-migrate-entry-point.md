---
id: 1061
title: 'C-16: GREEN — kanban-migrate entry point'
status: archived
priority: medium
created: 2026-04-21T10:44:12.239610+00:00
updated: 2026-04-24T08:29:50.381457+00:00
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
- [ ] AC-C38a: When `config`/`archive` lanes leave unresolved manual work, emit manual-action summary for `type:user-action` tasks. **Branch matrix:** archive lane failures for BOTH invalid `archival_reason` AND invalid `archival_refs` must each produce entries in `MANUAL ACTION SUMMARY:` on stderr (`migrate.py:500-503` → `:602-606`). **Summary-item proof required:** each archive failure variant must produce a ` - archive:` prefixed stderr line containing the archive file path AND the failure reason text (e.g. `invalid archival_reason`, `invalid archival_refs`). Path assertions must be anchored to summary-item lines, not satisfied by `FAIL` lines alone.
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
[[2026-04-24]]
## Builder Notes
- Implementation: no code changes in this cycle; verification-only builder pass for migrate entry-point task.
- Verification: quality-runner scoped run on serve/kanban/tests/test_migrate.py.
- Tests: 68 passed, 0 failed, 0 skipped.
- Lint: ruff clean on serve/kanban/src/owlbear_kanban/migrate.py and serve/kanban/tests/test_migrate.py.
- Coverage: module coverage for owlbear_kanban.migrate reported no-data-collected because migrate paths execute via subprocess CLI; functional AC evidence remains the fully passing TestFromAC suite.
- Evidence summary: AC-C31 through AC-C38a are covered by passing migrate tests, including strict lane-exclusivity and archival_refs branch-matrix proofs from latest test-writer cycle.

Post-task reflection:
- Problem faced: subprocess-heavy CLI suite limits direct coverage capture for the target module.
- Workaround applied: relied on quality-runner mandated scoped evidence (tests + lint) and explicit AC-mapped TestFromAC assertions.
- Pattern discovered: verification-only builder closes are valid when implementation is stable and proof-strengthening tests are green.
- Time sink: none in this cycle.
- Quality gap: no implementation or lint gaps observed in the scoped migrate slice.
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 68 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence. quality-runner reported coverage collection failure under xdist/subprocess execution (`unable_to_collect` / `No data collected`). This is not treated as a standalone failure; AC proof must come from explicit assertions.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C31 | `test_ac_c31_pyproject_scripts_exact_key_value` (`serve/kanban/tests/test_migrate.py:212`) with script mapping at `serve/kanban/pyproject.toml:8-9` | Yes | COVERED |
| AC-C32 | `test_ac_c32_lane_tasks_runs_only_task_lane` (`:230`), `test_ac_c32_lane_archive_runs_only_archive_lane` (`:245`), `test_ac_c32_lane_config_runs_only_config_lane` (`:257`), `test_ac_c32_all_lane_processes_task_archive_and_config_content` (`:285`), `test_ac_c32_archive_lane_does_not_touch_config` (`:317`), `test_ac_c32_config_lane_does_not_touch_archive` (`:336`), `test_ac_c32_single_lane_does_not_touch_other_dir` (`:758`) | Yes | COVERED |
| AC-C33 | Task happy-path coverage exists at `serve/kanban/tests/test_migrate.py:363`, `:375`, `:391`, but the task-body validation branch at `serve/kanban/src/owlbear_kanban/migrate.py:225` and canonical reorder step at `:233-234` have no AC-scoped proof | No for malformed task bodies and misordered frontmatter | MISSING |
| AC-C34 | `test_ac_c34_fully_migrated_board_zero_migrations` (`serve/kanban/tests/test_migrate.py:506`) and `test_ac_c34_modern_board_zero_migrations` (`:523`) | Yes | COVERED |
| AC-C35 | Archive invalid-refs variants are proved at `serve/kanban/tests/test_migrate.py:1143` and `:1173`, and missing-task-field variants at `:1026` and `:1061`, but the active-task idempotency predicate also requires canonical order at `serve/kanban/src/owlbear_kanban/migrate.py:155-168` and no AC-scoped test proves a misordered canonical task is migrated rather than skipped | No for misordered active-task frontmatter | MISSING |
| AC-C36 | `serve/kanban/tests/test_migrate.py:542`, `:556`, `:1211`, `:1224` | Yes | COVERED |
| AC-C37 | Strong subprocess-seam coverage at `serve/kanban/tests/test_migrate.py:1254`, `:1264`, `:1277`, `:1290`, `:1308` | Yes | COVERED |
| AC-C38 | `serve/kanban/tests/test_migrate.py:660`, `:666`, `:676` | Yes | COVERED |
| AC-C38a | `serve/kanban/tests/test_migrate.py:1362`, `:1412`, `:1429`, `:1474` | Yes | COVERED |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run on `serve/kanban/tests/test_migrate.py` | Yes | COVERED |

#### Security Review
- No issues found. Lane input is constrained by argparse choices at `serve/kanban/src/owlbear_kanban/migrate.py:559`, YAML uses safe/round-trip loaders, and writes remain atomic at `serve/kanban/src/owlbear_kanban/migrate.py:248`, `:318`, and `:456`.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected in the current state. Later retry work is additive; the latest cycle added tests without relaxing earlier AC assertions.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact script-mapping, invalid-refs stderr, lane-exclusivity, and manual-summary assertions exist in the current suite. |
| Negative/error-path coverage | WEAK | `_migrate_task_file()` rejects malformed task bodies via `parse_body(body_text)` at `serve/kanban/src/owlbear_kanban/migrate.py:225`, but no AC-scoped migrate test exercises that failure path. |
| Manual mutation reasoning | WEAK | `TestFromAC_CrashRecovery::test_ac_c37_no_partial_files_after_failure` patches `os.replace` in the parent process at `serve/kanban/tests/test_migrate.py:629-632`, but `_run_migrate()` always executes the SUT in a subprocess at `serve/kanban/tests/test_migrate.py:169-188`. The later subprocess crash suite proves AC-C37, but this earlier AC-owned class remains ineffective and misleading. |
| Test independence | STRONG | Cases build fresh boards under `tmp_path`; no shared mutable state was observed. |
| Descriptive names | STRONG | AC-tagged names are used consistently. |

#### Data Safety
- No issues found. Non-dry-run writes still go through `atomic_write` on task, archive, and config paths, and the subprocess crash-resume suite verifies no `.tmp-*` leftovers and clean convergence.

#### Implementation-Aware Gaps
1. Task-body validation failure path is untested. `parse_body(body_text)` is a contract step in Brief C §5.3 and is enforced at `serve/kanban/src/owlbear_kanban/migrate.py:225`, but the AC-scoped task-lane tests in `serve/kanban/tests/test_migrate.py:363-391` and `:1026-1061` cover only successful or missing-field task cases.
2. Misordered-but-otherwise-canonical active tasks are untested. `_is_task_migrated()` requires canonical frontmatter order at `serve/kanban/src/owlbear_kanban/migrate.py:155-168`, and `_migrate_task_file()` rewrites that order at `:233-234`, but no AC-scoped test proves a wrong-order task is migrated rather than skipped.
3. No scoped implementation defect was found in `migrate.py`; the remaining blocker is proof quality in the task-lane suite.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 6 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The older AC-C38a smoke test at `serve/kanban/tests/test_migrate.py:704-715` remains lax, but the later strict summary tests at `:1362`, `:1412`, `:1429`, and `:1474` now carry the real proof.
- Coverage remained unavailable for the known subprocess/xdist reason and was not treated as a separate failure.

### Failing Findings
1. AC-C33 proof gap: the current task suite does not exercise the malformed-task-body failure branch required by Brief C §5.3 step 4 (`serve/kanban/src/owlbear_kanban/migrate.py:225`).
2. AC-C35 proof gap: the active-task idempotency predicate depends on canonical field order (`serve/kanban/src/owlbear_kanban/migrate.py:155-168`), but no AC-scoped test proves a misordered task is migrated rather than skipped.
3. Test quality failure: the original `TestFromAC_CrashRecovery` class contains a parent-process `os.replace` monkeypatch that does not reach the subprocess SUT (`serve/kanban/tests/test_migrate.py:629-632` vs `_run_migrate()` at `:169-188`). Later subprocess tests repair AC-C37 coverage, but the AC-owned class itself remains weak.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:8-9`; `serve/kanban/tests/test_migrate.py:212` | PASS |
| AC-C32 | lane-routing and all six exclusivity directions are proved at `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, `:336`, `:758` | PASS |
| AC-C33 | Task happy-path transformations are proved, but task-body parse failure (`serve/kanban/src/owlbear_kanban/migrate.py:225`) and canonical reorder (`:233-234`) remain unproved in the AC suite | FAIL |
| AC-C34 | `serve/kanban/tests/test_migrate.py:506`, `:523` pin `Migrated: 0` | PASS |
| AC-C35 | Missing-field and archive-invalid-refs branches are proved, but active-task canonical-order idempotency at `serve/kanban/src/owlbear_kanban/migrate.py:155-168` is still unproved | FAIL |
| AC-C36 | `serve/kanban/tests/test_migrate.py:542`, `:556`, `:1211`, `:1224` prove no-write behavior | PASS |
| AC-C37 | subprocess crash/resume proof at `serve/kanban/tests/test_migrate.py:1254`, `:1264`, `:1277`, `:1290`, `:1308` | PASS |
| AC-C38 | `serve/kanban/tests/test_migrate.py:660`, `:666`, `:676` pin exit codes and fail lines | PASS |
| AC-C38a | manual-action summaries are proved for config migration, config rerun, invalid reason, and invalid refs at `serve/kanban/tests/test_migrate.py:1362`, `:1412`, `:1429`, `:1474` | PASS |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run: 68 passed, 0 failed | PASS |

### Deductions
- -0.06: AC-C33 task-body parse-failure branch is unproved.
- -0.05: AC-C35 active-task canonical-order idempotency branch is unproved.
- -0.04: AC-C37 retains an ineffective AC-owned crash test despite later strong subprocess proof.

### Confidence: 0.85
### Verdict: FAIL -> backlog
### Action
- Add an AC-scoped task-lane test proving malformed task bodies fail without writing and produce a `FAIL {path}: body parse error` stderr line.
- Add an AC-scoped task-lane/idempotency test proving a misordered-but-otherwise-canonical active task is migrated and rewritten into canonical order instead of being counted as `Already`.
- Replace or strengthen the older parent-process AC-C37 monkeypatch test so it exercises the subprocess seam rather than patching `os.replace` in the parent.
- No implementation fix is required to explain the current rejection; the remaining issue is proof quality in `serve/kanban/tests/test_migrate.py`.
- Loop-breaker routing applies. The task body already contains four prior `## Review Evidence` FAIL sections, so this fifth review failure returns to `backlog`.

### Reflection
- The latest retry did close the previously named archival_refs and lane-exclusivity gaps.
- The remaining misses are both in the task-lane branch matrix; they were hidden because earlier review cycles focused on archive/config gaps.
- A green subprocess CLI suite can still carry weak AC-owned tests if older parent-process monkeypatch cases are left in place.
[[2026-04-24]]
## Architecture Review (cycle 3)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration entry point, one domain |
| Interface clarity | REFINE | AC-C35 missing canonical-order idempotency test; AC-C33 parse_body branch needs dead-branch scope note |
| Dependency correctness | PASS | #1052 and #1059 both archived |
| Module layering | PASS | `migrate.py` imports from `storage_io` and `body_parser` only |
| TDD compliance | PASS | 68 tests all pass, tagged `tdd:green` |
| KISS/YAGNI | PASS | Minimal scope — migration script only |
| Premise challenge | PASS | Migration script required for Brief C schema cutover |
| Pattern consistency | PASS | Uses `atomic_write`, `ruamel.yaml`, `argparse` — consistent |
| Security surface | PASS | YAML safe loader, atomic writes, no shell/eval/network |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.57)
- Key concerns: (1) Brief C §5.3 step 4 explicitly names parse_body as an algorithm step — scoping it out without evidence is unjustified; (2) §5.3 step 2 explicitly requires canonical field order as an idempotency condition — not just an optimization; (3) refinements should be written into the task body, not prose-only carve-outs
- Architect response: ACCEPTED IN PART — the challenger is correct that canonical-order testing belongs in the AC (§5.3 step 2 explicitly names it). For parse_body, I investigated the actual code: `parse_body` in `body_parser.py:43-155` is a maximally permissive string-splitting state machine with no raising paths; `Section` model at `models.py:208-215` has no custom validators; `parse_body` always passes valid typed arguments. The try/except at `migrate.py:224-226` guards an unreachable branch. The spec itself notes: "markdown-it-py errors are extremely rare with CommonMark defaults; this is a sanity gate." Since the test suite runs via subprocess (`_run_migrate` at `test_migrate.py:169-188`), monkeypatching cannot reach the child process. This branch is excluded with evidence, not by fiat.

### AC Refinement Applied

**AC-C33** (revised): Per-lane algorithms match §5.3 (tasks, archive) and §5.4 (config) exactly. **Scope note:** §5.3 step 4 (`parse_body` validation) is a named safety gate. Code analysis confirms `parse_body` (`body_parser.py:43-155`) is a maximally permissive state machine with no raising codepaths on string input; `Section` model (`models.py:208-215`) has no custom validators. The try/except at `migrate.py:224-226` is unreachable dead code. Testing it requires monkeypatching, which cannot cross the subprocess test seam (`_run_migrate` at `test_migrate.py:169-188`). This branch is excluded from AC proof requirements.

**AC-C35** (revised): Idempotency checks follow lane-specific rules (contract-critical archive fields, canonical active-task fields). **Branch matrix:**
  - Archive invalid `archival_refs` (non-list): ✅ proved
  - Archive invalid `archival_refs` (boolean-containing list): ✅ proved
  - Active-task missing `created`: ✅ proved
  - Active-task missing `updated`: ✅ proved
  - Active-task non-canonical field order: ❌ MISSING — task with all correct fields in non-canonical order must be treated as not-yet-migrated (`Migrated: 1`, not `Already: 1`), per §5.3 step 2 condition 5

### Loop-Breaker Guidance (6th cycle — FINAL)

This task has cycled 5 times on proof-only gaps. Implementation is correct (confirmed by 5 independent reviews). Exactly 1 test is missing. The test-writer MUST add this 1 test and ONLY this 1 test:

**Test 1** — `TestFromAC_IdempotencyEdgeCases::test_ac_c35_task_misordered_canonical_fields_is_migrated_not_skipped`
```
Fixture: task file with ALL canonical fields present and correct values, but non-canonical order (e.g. `title` before `id`):
---
title: misordered task
id: 1001
status: todo
priority: medium
created: "2026-01-15T08:00:00+00:00"
updated: "2026-01-15T08:00:00+00:00"
tags: []
parent: null
depends_on: []
blocked: false
block_reason: null
claimed_at: null
archival_reason: null
archival_refs: []
---

## Notes

Content.

Action: _run_migrate(kanban_dir, lane="tasks")
Assert:
  1. result.returncode == 0
  2. stdout contains "Migrated: 1" (NOT "Already: 1")
  3. After migration, output file has `id` before `title` (canonical order restored)
```

### Completeness Matrix (for reviewer verification)

After adding Test 1, ALL AC-C35 idempotency branches are covered:

| Variant | Test |
|---------|------|
| Archive non-list refs | ✅ (existing) |
| Archive boolean-list refs | ✅ (existing) |
| Active-task missing created | ✅ (existing) |
| Active-task missing updated | ✅ (existing) |
| Active-task non-canonical order | ✅ (Test 1) |

AC-C33 parse_body dead-branch exclusion is evidenced:
- `parse_body` source: no raising paths (`body_parser.py:43-155`)
- `Section` model: no custom validators (`models.py:208-215`)
- Spec acknowledgment: "extremely rare... sanity gate" (paper-c.md §5.3 step 4)
- Test barrier: subprocess execution blocks monkeypatching

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC-C35 with canonical-order branch matrix item and precise loop-breaker guidance for 1 test. Added evidenced dead-branch scope exclusion for AC-C33 parse_body. Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: reviewer cited AC-C35 canonical-order idempotency branch gap; architect confirmed 1 test needed (loop-breaker cycle 3, 6th cycle guidance).
- Test file: `serve/kanban/tests/test_migrate.py` (69 tests total, 0 failed)
- Commit: `34add3f1` — "test: add AC proof test for C35 canonical-order idempotency branch (#1061, test-writer)"

### New tests added (1)

| New Test | AC Gap Addressed |
|----------|-----------------|
| `TestFromAC_IdempotencyEdgeCases::test_ac_c35_task_misordered_canonical_fields_is_migrated_not_skipped` | AC-C35 branch matrix — task with `title` before `id` (all correct values, non-canonical order) → `Migrated: 1` (not `Already: 1`); after migration `id` appears before `title` in output file |

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (unchanged) |
| AC-C32 | COVERED (unchanged — all 6 cross-lane exclusivity directions proved) |
| AC-C33 | COVERED (parse_body dead-branch exclusion confirmed by architect with code evidence) |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED — all 5 branch-matrix variants now proved: archive non-list refs ✅, archive boolean-list refs ✅, missing created ✅, missing updated ✅, non-canonical order ✅ |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED (unchanged) |

### Execution
- pytest: 69 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean
- New test passes because the implementation is already correct at `_is_task_migrated()` via `_has_canonical_order()`; this proves the specific branch the architect's loop-breaker required.
[[2026-04-24]]
## Builder Notes
- Files changed: none (verification-only cycle).
- Test results: `serve/kanban/tests/test_migrate.py` -> 69 passed, 0 failed.
- Lint status: `ruff` clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- Coverage: not re-measured in this scoped close; known subprocess-driven CLI path can report `no-data-collected` for module coverage.
- Evidence summary: AC proof suite remains fully green after latest test-writer additions, including strict lane exclusivity and AC-C35 branch-matrix assertions.
- Fixes applied: none in this builder cycle (implementation already satisfied AC).
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 69 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence because the suite exercises the CLI through `python -m owlbear_kanban.migrate` subprocesses. I did not treat that as a standalone failure.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C31 | `serve/kanban/pyproject.toml:8-9`; `serve/kanban/tests/test_migrate.py:212` | Yes | COVERED |
| AC-C32 | `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, `:336`, `:758` | Yes | COVERED |
| AC-C33 | `serve/kanban/tests/test_migrate.py:363`, `:375`, `:391`, `:409`, `:420`, `:436`, `:462`, `:474`, `:871`, `:912`, `:928`; latest Architecture Review cycle 3 excludes the dead `parse_body` failure guard using `serve/kanban/src/owlbear_kanban/body_parser.py:43` and `serve/kanban/src/owlbear_kanban/models.py:219` | Yes for the live contract surface | COVERED |
| AC-C34 | `serve/kanban/tests/test_migrate.py:506`, `:523` | Yes | COVERED |
| AC-C35 | `serve/kanban/tests/test_migrate.py:450`, `:485`, `:1008`, `:1026`, `:1061`, `:1143`, `:1173`, `:1202`; predicate lines `serve/kanban/src/owlbear_kanban/migrate.py:155-168` | Yes | COVERED |
| AC-C36 | `serve/kanban/tests/test_migrate.py:542`, `:556`, `:569`, `:583`, `:1264`, `:1277` | Yes for the write-suppression contract on each live lane path | COVERED |
| AC-C37 | `serve/kanban/tests/test_migrate.py:1296`, `:1307`, `:1317`, `:1330`, `:1343`, `:1361` | Yes | COVERED |
| AC-C38 | `serve/kanban/tests/test_migrate.py:666`, `:676`; fail-line implementation at `serve/kanban/src/owlbear_kanban/migrate.py:500-503`, `:530-531` | Yes for exit-code behavior and failed-file reporting | COVERED |
| AC-C38a | `serve/kanban/tests/test_migrate.py:1415`, `:1423`, `:1429`, `:1435`, `:1443`, `:1451`, `:1465`, `:1482`, `:1509`, `:1527`; summary-item implementation at `serve/kanban/src/owlbear_kanban/migrate.py:500-503`, summary block at `:602-606` | No. The archive invalid-reason tests assert only fail-line text plus summary header, and the invalid-refs test asserts the path appears somewhere in stderr, which is already satisfied by the fail line. A regression that drops archive summary-item lines while keeping the fail line and header would still pass. | MISSING |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run | Yes | COVERED |

#### Security Review
- No issues found. YAML parsing stays on the safe or round-trip loaders, writes remain atomic, and no shell, network, eval, or secret surface was introduced.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected in the current retry. The latest retry is additive only (`serve/kanban/tests/test_migrate.py:1202`).

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most ACs are pinned directly, but AC-C38a archive summary tests do not assert a per-file summary-item line. |
| Negative/error-path coverage | ADEQUATE | Archive invalid-reason and invalid-refs paths execute, but the summary-entry obligation is not directly asserted. |
| Manual mutation reasoning | WEAK | A mutant that preserves `FAIL {path}: {reason}` and `MANUAL ACTION SUMMARY:` while removing archive summary-item lines would still satisfy `serve/kanban/tests/test_migrate.py:1451`, `:1465`, and likely `:1527` because those checks do not anchor the file-path assertion to the summary block. |
| Test independence | STRONG | Each case builds an isolated board under `tmp_path`. |
| Descriptive names | STRONG | AC-tagged names remain clear throughout the suite. |

#### Data Safety
- No issues found. Task, archive, and config writes still go through `atomic_write`, and the subprocess crash-resume suite remains the real AC-C37 proof.

#### Implementation-Aware Gaps
- No new implementation defect found in `serve/kanban/src/owlbear_kanban/migrate.py`.
- The blocker is proof quality in `serve/kanban/tests/test_migrate.py` for AC-C38a archive manual-action summary entries.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 7 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- I did not gate on the older parent-process crash tests at `serve/kanban/tests/test_migrate.py:610` and `:637`; the subprocess suite at `:1296-1361` carries the binding AC-C37 proof.
- I did not re-open the earlier `parse_body` concern; the latest Architecture Review cycle 3 grounded that exclusion in actual source analysis.
- `serve/kanban/tests/test_migrate.py:1-5` still carries stale RED-phase header text. Informational only.

### Failing Findings
1. AC-C38a proof gap remains. The task AC requires archive failures for both invalid `archival_reason` and invalid `archival_refs` to produce entries in `MANUAL ACTION SUMMARY:`. The implementation does append per-file archive items at `serve/kanban/src/owlbear_kanban/migrate.py:500-503`, but the tests do not directly prove those entry lines exist in the summary block. `serve/kanban/tests/test_migrate.py:1451` and `:1465` stop at fail-line text plus summary header, and `serve/kanban/tests/test_migrate.py:1527` checks only that the path appears somewhere in stderr, which the fail line already satisfies.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:8-9`; `serve/kanban/tests/test_migrate.py:212` | PASS |
| AC-C32 | `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, `:336`, `:758` | PASS |
| AC-C33 | `serve/kanban/tests/test_migrate.py:363`, `:375`, `:391`, `:409`, `:420`, `:436`, `:462`, `:474`, `:871`, `:912`, `:928`; dead-branch exclusion grounded by `serve/kanban/src/owlbear_kanban/body_parser.py:43` and `serve/kanban/src/owlbear_kanban/models.py:219` | PASS |
| AC-C34 | `serve/kanban/tests/test_migrate.py:506`, `:523` | PASS |
| AC-C35 | `serve/kanban/tests/test_migrate.py:450`, `:485`, `:1008`, `:1026`, `:1061`, `:1143`, `:1173`, `:1202` | PASS |
| AC-C36 | `serve/kanban/tests/test_migrate.py:542`, `:556`, `:569`, `:583`, `:1264`, `:1277` | PASS |
| AC-C37 | `serve/kanban/tests/test_migrate.py:1296`, `:1307`, `:1317`, `:1330`, `:1343`, `:1361` | PASS |
| AC-C38 | `serve/kanban/tests/test_migrate.py:666`, `:676`; `serve/kanban/src/owlbear_kanban/migrate.py:500-503`, `:530-531` | PASS |
| AC-C38a | `serve/kanban/tests/test_migrate.py:1451`, `:1465`, `:1527`; `serve/kanban/src/owlbear_kanban/migrate.py:500-503`, `:602-606` | FAIL |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run: 69 passed, 0 failed | PASS |

### Deductions
- -0.08: AC-C38a archive invalid-reason summary-entry proof is missing.
- -0.04: AC-C38a archive invalid-refs summary assertion is not anchored to the summary block and can be satisfied by the fail line alone.

### Confidence: 0.88
### Verdict: FAIL to backlog
### Action
- Add a strict `TestFromAC_ManualActionSummaryStrict` case for invalid `archival_reason` that asserts a summary-item line containing `archive:`, the archive path, and the reason text appears after the summary header.
- Tighten the invalid `archival_refs` summary test so the path assertion is anchored to the summary-item line rather than any stderr occurrence.
- Loop-breaker routing applies. The task file already contains five prior `## Review Evidence` sections at `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:67`, `:169`, `:303`, `:502`, and `:727`, so this sixth reviewer rejection returns to `backlog`.

### Reflection
- Latest architecture refinements should be treated as binding scope updates, but they do not excuse new AC-grounded proof gaps found in the current suite.
- Header-plus-path-anywhere assertions are not enough when the contract requires a specific summary-block entry.
- Subprocess-heavy CLI suites need especially direct stderr-line assertions because module coverage is expected to stay unavailable in scoped runs.
[[2026-04-24]]
## Architecture Review (cycle 4)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration entry point, one domain |
| Interface clarity | REFINE | AC-C38a missing summary-item assertion requirement (root cause of 6th reviewer FAIL) |
| Dependency correctness | PASS | #1052 and #1059 both archived |
| Module layering | PASS | `migrate.py` imports from `storage_io` and `body_parser` only |
| TDD compliance | PASS | 69 tests all pass, tagged `tdd:green` |
| KISS/YAGNI | PASS | Minimal scope — migration script only |
| Premise challenge | PASS | Migration script required for Brief C schema cutover |
| Pattern consistency | PASS | Uses `atomic_write`, `ruamel.yaml`, `argparse` — consistent |
| Security surface | PASS | YAML safe loader, atomic writes, no shell/eval/network |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.54)
- Key concerns: (1) proposed refinement dropped reason-text requirement that reviewer explicitly demanded; (2) header-only proof is insufficient since summary-item lines are emitted in a separate code path; (3) history of under-inclusive architect approvals weakens diminishing-returns argument
- Architect response: ACCEPTED — the challenger is correct on all three points. Strengthened AC-C38a to require reason-text assertions anchored to summary-item lines. Previous refinement was weaker than reviewer's stated requirement.

### AC Refinement Applied

**AC-C38a** (revised): Added explicit summary-item proof requirement. Each archive failure variant must produce a ` - archive:` prefixed stderr line containing the archive file path AND the failure reason text. Path assertions must be anchored to summary-item lines, not satisfied by `FAIL` lines alone.

This addresses the reviewer's exact requirements from cycle 6:
1. Invalid `archival_reason`: summary-item line with `archive:`, path, and reason text after summary header
2. Invalid `archival_refs`: path assertion anchored to summary-item line rather than any stderr occurrence

### Loop-Breaker Guidance (8th cycle — FINAL)

This task has cycled 6 times on proof-only gaps. Implementation is correct (confirmed by ALL 6 reviews). The test-writer must tighten 2 existing test assertions. No new tests.

**Fix 1** — Tighten `test_ac_c38a_archive_invalid_reason_produces_fail_line_on_stderr` (line ~1460):
```
Current assertions: FAIL in stderr, manual-action required in stderr, MANUAL ACTION SUMMARY: in stderr
Add: find a stderr line starting with " - archive:" that contains BOTH the archive file path (or filename "0001-bad.md") AND the text "invalid archival_reason"
```

**Fix 2** — Tighten `test_ac_c38a_archive_invalid_refs_emits_manual_action_summary` (line ~1527):
```
Current assertions: MANUAL ACTION SUMMARY: in stderr, path appears in stderr
Replace path assertion: find a stderr line starting with " - archive:" that contains BOTH the archive file path (or filename "0001-invalid-refs.md") AND the text "invalid archival_refs"
```

### Assertion Pattern (for test-writer reference)

The implementation at `migrate.py:500-503` appends `f"archive: {path} - {reason}"` to `manual_actions`. The emission at `migrate.py:602-606` writes `f" - {item}\n"` per item. So each summary-item line looks like:
```
 - archive: /path/to/0001-bad.md - manual-action required: invalid archival_reason
```

The assertion should find a line matching this shape:
```python
summary_items = [line for line in result.stderr.splitlines() if line.strip().startswith("- archive:")]
assert len(summary_items) >= 1
assert "0001-bad.md" in summary_items[0]
assert "invalid archival_reason" in summary_items[0]  # Fix 1 only
assert "invalid archival_refs" in summary_items[0]  # Fix 2 only
```

### Completeness Matrix

After these 2 assertion tightenings, ALL AC-C38a variants are proved with full summary-item evidence:

| Variant | Test | Summary-item proof |
|---------|------|--------------------|
| Archive invalid reason | `test_ac_c38a_archive_invalid_reason_produces_fail_line_on_stderr` | ✅ (after Fix 1) |
| Archive invalid refs (non-list) | `test_ac_c38a_archive_invalid_refs_emits_manual_action_summary` | ✅ (after Fix 2) |
| Config fresh migration stubs | `test_ac_c38a_config_summary_mentions_*` | ✅ (existing — field names proved) |
| Config rerun stubs | `test_ac_c38a_config_rerun_*` | ✅ (existing — header + fields proved) |

### Verdict: REFINE → APPROVE
### Action Taken: Refined AC-C38a with explicit summary-item proof requirement including reason-text assertions. Added loop-breaker guidance with exact assertion patterns for 2 existing tests. Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: reviewer cited AC-C38a summary-item assertions too weak — path assertions were not anchored to `- archive:` summary-item lines. Architect loop-breaker (cycle 4, 8th cycle) specified exactly 2 assertion tightenings; no new tests needed.
- Test file: `serve/kanban/tests/test_migrate.py` (69 tests total, 0 failed)
- Commit: `4891b5cc` — "test: tighten AC-C38a summary-item assertions for archive invalid-reason and invalid-refs (#1061, test-writer)"

### Changes made (2 assertion tightenings, no new tests)

| Test | Change |
|------|--------|
| `TestFromAC_ManualActionSummaryStrict::test_ac_c38a_archive_invalid_reason_produces_fail_line_on_stderr` | Added: find `- archive:` summary-item line, assert contains `0001-bad.md` AND `invalid archival_reason` |
| `TestFromAC_ManualActionSummaryStrict::test_ac_c38a_archive_invalid_refs_emits_manual_action_summary` | Replaced loose `str(arc_file) in result.stderr` with: find `- archive:` summary-item line, assert contains `0001-invalid-refs.md` AND `invalid archival_refs` |

### Assertion pattern applied
```python
summary_items = [line for line in result.stderr.splitlines() if line.strip().startswith("- archive:")]
assert len(summary_items) >= 1
assert "{filename}" in summary_items[0]
assert "{reason_text}" in summary_items[0]
```

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (unchanged) |
| AC-C32 | COVERED (unchanged — all 6 cross-lane exclusivity directions proved) |
| AC-C33 | COVERED (unchanged — dead-branch exclusion confirmed) |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED (unchanged — all 5 branch-matrix variants proved) |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED — invalid-reason and invalid-refs summary-item lines now proved with path AND reason-text assertions anchored to `- archive:` lines |

### Execution
- pytest: 69 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean
[[2026-04-24]]
## Builder Notes
- Files changed: none (verification-only close).
- Tests: 69 passed, 0 failed, 0 skipped in serve/kanban/tests/test_migrate.py.
- Lint: clean for serve/kanban/src/owlbear_kanban/migrate.py and serve/kanban/tests/test_migrate.py.
- Coverage: module coverage remains unavailable for this subprocess-driven CLI suite; functional AC evidence is the fully passing TestFromAC suite.
- Evidence summary: AC-C38a summary-item assertion tightening from test-writer remains green along with full migrate suite.

Post-task reflection:
- Problem faced: none in this cycle; this was a verification gate.
- Workaround applied: used scoped quality-runner evidence only, with no incidental edits.
- Pattern discovered: verification-only close is appropriate when implementation is stable and AC-proof tests are strengthened upstream.
- Time sink: none.
- Quality gap: none observed in the scoped migrate module and test slice.
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 69 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence because the CLI suite executes the entry point in subprocesses. quality-runner reported no data collected. This was not treated as a standalone failure.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC-C31 | Exact console-script mapping at `serve/kanban/pyproject.toml:9` with direct proof at `serve/kanban/tests/test_migrate.py:212` | COVERED |
| AC-C32 | Lane selection and all six exclusivity directions are asserted at `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, `:336`, `:758` | COVERED |
| AC-C33 | Brief C requires exact task defaults, exact timestamp normalisation for `created`, `updated`, and `claimed_at`, exact archive refs autofill, and verbatim archive body preservation (`.owlbear/briefs/draft-kanban-storage-c-2026-04-20/paper-c.md:468-498`). The live tests at `serve/kanban/tests/test_migrate.py:375-389`, `:391-407`, `:475-483`, `:871-884`, and `:912-926` do not prove those exact contracts. | MISSING |
| AC-C34 | Idempotency counts pinned at `serve/kanban/tests/test_migrate.py:506`, `:523` | COVERED |
| AC-C35 | Branch-matrix proof exists at `serve/kanban/tests/test_migrate.py:1026`, `:1061`, `:1143`, `:1173`, `:1202` against `_is_task_migrated()` at `serve/kanban/src/owlbear_kanban/migrate.py:155` | COVERED |
| AC-C36 | Dry-run no-write proof at `serve/kanban/tests/test_migrate.py:542`, `:556`, `:1211`, `:1224` | COVERED |
| AC-C37 | Subprocess crash-resume proof at `serve/kanban/tests/test_migrate.py:1296`, `:1307`, `:1317`, `:1330`, `:1343`, `:1361`; atomic_write cleanup primitive separately covered at `serve/kanban/tests/test_storage_io.py:194-212` | COVERED |
| AC-C38 | Exit-code and FAIL-line proof at `serve/kanban/tests/test_migrate.py:660`, `:666`, `:676` | COVERED |
| AC-C38a | Manual-action summary proof now anchored to `- archive:` summary-item lines at `serve/kanban/tests/test_migrate.py:1451`, `:1541`; implementation path in `serve/kanban/src/owlbear_kanban/migrate.py:479`, `:546` | COVERED |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run on `serve/kanban/tests/test_migrate.py` | COVERED |

#### Security Review
- No issues found. YAML parsing stays on safe or round-trip loaders, writes remain atomic, and no shell, network, eval, or secret surface was introduced.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected in the current retry. The latest retry only tightened AC-C38a summary-item checks.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | WEAK | `serve/kanban/tests/test_migrate.py:375-389` checks only presence of `archival_reason` / `archival_refs`, not the required `null` / `[]` values. `serve/kanban/tests/test_migrate.py:391-407` checks only that some `+00:00` appears. `serve/kanban/tests/test_migrate.py:912-926` checks only substring containment instead of exact body equality. |
| Negative/error-path coverage | ADEQUATE | Invalid archive reason/refs, config manual-action, idempotency edge cases, and crash-resume paths are exercised. |
| Manual mutation reasoning | WEAK | A mutant that writes `archival_reason: completed` or non-empty `archival_refs` into migrated tasks, omits non-null `claimed_at` normalisation, or rewrites archive body around the preserved sentence would still satisfy the current AC-C33 tests. |
| Test independence | STRONG | Cases build isolated boards under `tmp_path`. |
| Descriptive names | STRONG | AC-tagged names remain clear throughout the suite. |

#### Data Safety
- No implementation data-safety issues found. `migrate.py` still delegates writes through `atomic_write` at `serve/kanban/src/owlbear_kanban/migrate.py:248` and `:318`, and the primitive has direct cleanup coverage in `serve/kanban/tests/test_storage_io.py:194-212`.

#### Implementation-Aware Gaps
1. Task-lane exactness gap. `_ACTIVE_TASK_DEFAULTS` defines `archival_reason=None` and `archival_refs=[]` at `serve/kanban/src/owlbear_kanban/migrate.py:79-87` and applies them at `:220`, but `serve/kanban/tests/test_migrate.py:375-389` checks only field presence. `serve/kanban/tests/test_migrate.py:391-407` checks only that some `+00:00` exists, and the legacy-task fixture at `serve/kanban/tests/test_migrate.py:78` does not exercise a non-null `claimed_at`, so the `claimed_at` branch in `_TS_FIELDS` at `serve/kanban/src/owlbear_kanban/migrate.py:162` and `:213` remains unproved.
2. Archive-lane exactness gap. `_migrate_archive_file()` auto-fills missing refs at `serve/kanban/src/owlbear_kanban/migrate.py:305-307` and writes the original `body_text` back at `:279` and `:315`, but `serve/kanban/tests/test_migrate.py:475-483` and `:871-884` check only presence of `archival_refs`, and `serve/kanban/tests/test_migrate.py:912-926` checks only that one sentence survives somewhere in the body rather than exact byte-for-byte body preservation.
3. No scoped implementation defect was found in `serve/kanban/src/owlbear_kanban/migrate.py`; the remaining blocker is proof quality in `serve/kanban/tests/test_migrate.py`.

### Failing Findings
1. AC-C33 proof gap: task-lane assertions are still too weak to prove the exact default values and exact timestamp normalisation required by Brief C. Evidence: `serve/kanban/src/owlbear_kanban/migrate.py:79-87`, `:162`, `:213`, `:220`; `serve/kanban/tests/test_migrate.py:375-389`, `:391-407`, `:78`.
2. AC-C33 proof gap: archive-lane assertions are still too weak to prove exact `archival_refs: []` autofill and verbatim body preservation. Evidence: `serve/kanban/src/owlbear_kanban/migrate.py:279`, `:305-307`, `:315`; `serve/kanban/tests/test_migrate.py:475-483`, `:871-884`, `:912-926`.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:9`; `serve/kanban/tests/test_migrate.py:212` | PASS |
| AC-C32 | `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, `:336`, `:758` | PASS |
| AC-C33 | Exact task-default, claimed_at-normalisation, archive-refs-default, and archive-body-verbatim proof remains incomplete in `serve/kanban/tests/test_migrate.py` | FAIL |
| AC-C34 | `serve/kanban/tests/test_migrate.py:506`, `:523` | PASS |
| AC-C35 | `serve/kanban/tests/test_migrate.py:1026`, `:1061`, `:1143`, `:1173`, `:1202`; `serve/kanban/src/owlbear_kanban/migrate.py:155` | PASS |
| AC-C36 | `serve/kanban/tests/test_migrate.py:542`, `:556`, `:1211`, `:1224` | PASS |
| AC-C37 | `serve/kanban/tests/test_migrate.py:1296`, `:1307`, `:1317`, `:1330`, `:1343`, `:1361`; `serve/kanban/tests/test_storage_io.py:194-212` | PASS |
| AC-C38 | `serve/kanban/tests/test_migrate.py:660`, `:666`, `:676` | PASS |
| AC-C38a | `serve/kanban/tests/test_migrate.py:1451`, `:1541`; `serve/kanban/src/owlbear_kanban/migrate.py:479`, `:546` | PASS |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run: 69 passed, 0 failed | PASS |

### Deductions
- -0.06: AC-C33 task defaults and claimed_at normalisation are unproved with exact assertions.
- -0.05: AC-C33 archive refs autofill and body-verbatim behaviour are unproved with exact assertions.
- -0.03: mutation resistance remains weak on the live AC-C33 contract.

### Confidence
- 0.86

### Verdict
- FAIL to backlog

### Action
- Tighten AC-C33 task-lane tests to assert exact `archival_reason: null` and exact `archival_refs: []` output values, and add a non-null `claimed_at` case that proves explicit `+00:00` normalisation on that field.
- Tighten AC-C33 archive-lane tests to assert exact `archival_refs: []` autofill and exact post-migration body equality, not substring containment.
- No implementation fix is required in `serve/kanban/src/owlbear_kanban/migrate.py`; this rejection is on proof quality in `serve/kanban/tests/test_migrate.py`.
- Loop-breaker routing applies. The task file `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md` already contains six prior `## Review Evidence` sections at lines 67, 169, 303, 502, 727, and 950, so this reviewer rejection returns to backlog.

### Reflection
- Later retries fully closed the AC-C38a summary-item gap, but AC-C33 still hides exact-value proof holes inside otherwise-green happy-path assertions.
- For migration tasks, field presence is not enough when the contract specifies the exact default value or exact byte preservation.
- Subprocess-heavy CLI suites need direct file-equality and exact-output assertions because green counts and unavailable module coverage can mask weak proofs.
[[2026-04-24]]
## Architecture Review (cycle 5)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration entry point, one domain |
| Interface clarity | REFINE | AC-C33 "exactly" is infinitely divisible — root cause of 7-cycle loop. Replacing with enumerated sub-contracts. |
| Dependency correctness | PASS | #1052 and #1059 both archived |
| Module layering | PASS | `migrate.py` imports from `storage_io` and `body_parser` only |
| TDD compliance | PASS | 69 tests all pass, tagged `tdd:green` |
| KISS/YAGNI | PASS | Minimal scope — migration script only |
| Premise challenge | PASS | Migration script required for Brief C schema cutover |
| Pattern consistency | PASS | Uses `atomic_write`, `ruamel.yaml`, `argparse` — consistent |
| Security surface | PASS | YAML safe loader, atomic writes, no shell/eval/network |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.52)
- Key concerns: (1) config lane exact-value contracts omitted — reviewer can attack next; (2) preserve-if-present branch untested — mutant that overwrites all defaults escapes; (3) repeated "exactly N tests" claims disproved by next reviewer
- Architect response: ACCEPTED — all three concerns are valid. This cycle addresses all three by enumerating every AC-C33 sub-contract across all three lanes, including config derived values and preserve-if-present. The root cause of the loop is that "match §5.3/§5.4 exactly" is infinitely divisible; this refinement replaces it with a closed, enumerable set.

### AC-C33 Refinement — Definitive Sub-Contract Enumeration

**AC-C33** (revised): Per-lane algorithms match §5.3 (tasks, archive) and §5.4 (config). Proof obligations are enumerated below. Items marked ✅ are proved by existing tests. Items marked ❌ require changes specified in Loop-Breaker Guidance.

**Task lane sub-contracts:**
- T1: Remove `claimed_by` field → ✅ proved (`test_ac_c33_tasks_lane_removes_claimed_by`)
- T2: Normalise `created` and `updated` to `+00:00` (per-field, not global) → ❌ TIGHTEN
- T3: Normalise non-null `claimed_at` to `+00:00` → ❌ ADD TEST
- T4: Inject ALL `_ACTIVE_TASK_DEFAULTS` with exact values when absent → ❌ TIGHTEN (exact values for all 8 fields)
- T5: Preserve existing non-default field values unchanged during migration → ❌ ADD TEST
- T6: Reorder frontmatter to canonical field order → ✅ proved (AC-C35 misordered test)

**Archive lane sub-contracts:**
- A1: Auto-fill `archival_reason: completed` when absent → ✅ proved (exact value in existing test)
- A2: Auto-fill `archival_refs: []` when absent (exact value) → ❌ TIGHTEN
- A3: Preserve body text verbatim (exact equality, not substring) → ❌ TIGHTEN
- A4: Fail on invalid `archival_reason` → ✅ proved
- A5: Fail on invalid `archival_refs` → ✅ proved

**Config lane sub-contracts:**
- C1: Convert statuses from `[{name: ...}]` to `[str]` → ✅ proved
- C2: Drop legacy fields (board, version, tasks_dir, archive_dir, defaults, activity_log) → ✅ proved
- C3: Add new required fields with correct presence → ✅ proved
- C4: Derive `entry_status` from legacy `defaults.status`; preserve `claim_timeout`, `next_id`, `priorities` → ❌ TIGHTEN
- C5: Hard-coded constants (`wave_size`, `agent_map`, `agent_types`, `agent_compatibility`, `status_predicates`) → EXCLUDED — implementation constants; testing them duplicates source code. `wave_size: 4` is included in C4 as a low-cost check.
- C6: Hard-coded list constants (`non_impl_tags` items, `archival_reasons` items) → EXCLUDED — same rationale; these lists may change between versions

**Excluded (with prior evidence):**
- `parse_body` dead branch → excluded in Architecture Review cycle 3 with source analysis of `body_parser.py:43-155` and `models.py:208-215`
- AC-C37 ineffective parent-process monkeypatch test → not AC compliance; subprocess crash suite carries real proof

### Loop-Breaker Guidance (10th cycle — FINAL)

This task has cycled 7 times on proof-only gaps. Implementation is correct (confirmed by ALL 7 reviews). The test-writer must make exactly 7 changes: 5 assertion tightenings + 2 new tests.

**Change 1** — TIGHTEN `test_ac_c33_tasks_lane_adds_archival_fields` (covers T4)
Rename to `test_ac_c33_tasks_lane_adds_all_defaults_with_exact_values`.
Replace the two presence checks with exact-value checks for ALL 8 `_ACTIVE_TASK_DEFAULTS` fields:
```python
content = task_file.read_text(encoding="utf-8")
assert "archival_reason: null" in content
assert "archival_refs: []" in content
assert "tags: []" in content
assert "parent: null" in content
assert "depends_on: []" in content
assert "blocked: false" in content
assert "block_reason: null" in content
assert "claimed_at: null" in content
```

**Change 2** — TIGHTEN `test_ac_c33_tasks_lane_normalises_timestamps_to_utc` (covers T2)
Replace the global `"+00:00" in content` with per-field checks:
```python
lines = content.splitlines()
created_lines = [l for l in lines if l.strip().startswith("created:")]
updated_lines = [l for l in lines if l.strip().startswith("updated:")]
assert created_lines, "created field missing"
assert updated_lines, "updated field missing"
assert "+00:00" in created_lines[0], "created not normalised"
assert "+00:00" in updated_lines[0], "updated not normalised"
```

**Change 3** — ADD `TestFromAC_LaneAlgorithms::test_ac_c33_tasks_lane_normalises_nonnull_claimed_at` (covers T3)
```
Fixture: task with created/updated already +00:00 but claimed_at: "2026-01-20T10:00:00" (no tz)
Action: _run_migrate(kanban_dir, lane="tasks")
Assert:
  1. claimed_at line in output contains "+00:00"
  2. claimed_at line does NOT contain "null" (value was preserved, not defaulted)
```

**Change 4** — ADD `TestFromAC_LaneAlgorithms::test_ac_c33_tasks_lane_preserves_existing_nonnull_values` (covers T5)
```
Fixture: task with created/updated +00:00, tags: [bug], parent: 42, but missing archival_reason/archival_refs
Action: _run_migrate(kanban_dir, lane="tasks")
Assert:
  1. "- bug" in content (tags preserved)
  2. "parent: 42" in content (parent preserved)
  3. "archival_reason: null" in content (missing field added with default)
  4. "archival_refs: []" in content (missing field added with default)
```

**Change 5** — TIGHTEN `test_ac_c33_archive_lane_adds_archival_refs` (covers A2)
```
Replace: assert "archival_refs:" in content
With:    assert "archival_refs: []" in content
```

**Change 6** — TIGHTEN `test_ac_c33_archive_preserves_body_text_verbatim` (covers A3)
```
Replace: assert "Original body content with *markdown*." in after_fm
With:    assert after_fm == body
```

**Change 7** — TIGHTEN `test_ac_c33_config_lane_adds_new_required_fields` (covers C4)
After the existing presence checks, add exact-value assertions for derived and preserved fields:
```python
assert "entry_status: research" in content
assert "claim_timeout: 1h" in content
assert "next_id: 1001" in content
assert "wave_size: 4" in content
```

### Completeness Matrix (for reviewer verification)

After all 7 changes, every AC-C33 sub-contract is either PROVED or EXCLUDED with evidence:

| Sub-contract | Proof |
|-------------|-------|
| T1 claimed_by removal | ✅ existing |
| T2 per-field timestamp normalisation | ✅ Change 2 |
| T3 claimed_at normalisation | ✅ Change 3 |
| T4 all defaults with exact values | ✅ Change 1 |
| T5 preserve-if-present | ✅ Change 4 |
| T6 canonical order | ✅ AC-C35 existing |
| A1 archival_reason auto-fill | ✅ existing |
| A2 archival_refs exact auto-fill | ✅ Change 5 |
| A3 body verbatim exact | ✅ Change 6 |
| A4 invalid reason failure | ✅ existing |
| A5 invalid refs failure | ✅ existing |
| C1 statuses conversion | ✅ existing |
| C2 legacy field removal | ✅ existing |
| C3 new field presence | ✅ existing |
| C4 derived/preserved values | ✅ Change 7 |
| C5 hard-coded stubs | EXCLUDED (implementation constants) |
| C6 hard-coded lists | EXCLUDED (implementation constants) |

### Verdict: REFINE → APPROVE
### Action Taken: Replaced vague "match exactly" AC-C33 with 17 enumerated sub-contracts (12 proved, 5 excluded with evidence). Provided loop-breaker guidance with exact assertion patterns for 7 changes (5 tightenings + 2 new tests). Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: reviewer cited AC-C33 proof gaps — task-lane defaults/timestamps/claimed_at/preserve-if-present weak assertions; archive body verbatim weak; config C4 derived values absent.
- Test file: `serve/kanban/tests/test_migrate.py` (71 tests total, 0 failed)
- Commit: `05697f34` — "test: tighten AC-C33 exact-value assertions and add T3/T4/T5/C4 branch proofs (#1061, test-writer)"

### Changes made (7 per architect cycle-5 loop-breaker guidance)

| Change | Type | AC Sub-contract |
|--------|------|-----------------|
| Rename+tighten `test_ac_c33_tasks_lane_adds_archival_fields` → `test_ac_c33_tasks_lane_adds_all_defaults_with_exact_values` | Tighten | T4: all 8 `_ACTIVE_TASK_DEFAULTS` checked with null/empty-list exact values |
| Tighten `test_ac_c33_tasks_lane_normalises_timestamps_to_utc` | Tighten | T2: per-field `created:` and `updated:` lines checked individually |
| Add `test_ac_c33_tasks_lane_normalises_nonnull_claimed_at` | New | T3: non-null `claimed_at` normalised to `+00:00`, not set to null |
| Add `test_ac_c33_tasks_lane_preserves_existing_nonnull_values` | New | T5: existing `tags: [bug]`, `parent: 42` preserved; absent archival fields injected |
| Tighten `test_ac_c33_archive_lane_adds_archival_refs` | Tighten | A2: `archival_refs: []` exact value (not just presence) |
| Tighten `test_ac_c33_archive_preserves_body_text_verbatim` | Tighten | A3: `after_fm == body` (exact equality, not substring) |
| Tighten `test_ac_c33_config_lane_adds_new_required_fields` | Tighten | C4: `entry_status: research`, `claim_timeout: 1h`, `next_id: 1001`, `wave_size: 4` exact values |

Note: null-value assertions use `"key: null\n" in content or "key:\n" in content` pattern to accept both ruamel.yaml null renderings (bare key vs. explicit null), while remaining mutation-resistant against wrong values (e.g., `key: completed` would fail both checks).

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (unchanged) |
| AC-C32 | COVERED (unchanged — all 6 cross-lane exclusivity directions proved) |
| AC-C33 | COVERED — all sub-contracts per architect cycle-5 completeness matrix: T1✅ T2✅ T3✅ T4✅ T5✅ T6✅ A1✅ A2✅ A3✅ A4✅ A5✅ C1✅ C2✅ C3✅ C4✅ C5/C6 EXCLUDED |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED (unchanged — all 5 branch-matrix variants proved) |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED (unchanged) |

### Execution
- pytest: 71 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean
- All 7 changes produce passing tests because implementation is already correct; these prove the specific sub-contracts the reviewer required.
[[2026-04-24]]
## Builder Notes
- Implementation: no code changes in this builder cycle (verification-only pass).
- Files touched: none.
- Tests: quality-runner scoped run on serve/kanban/tests/test_migrate.py reported 71 passed, 0 failed, 0 skipped.
- Lint: ruff clean for serve/kanban/src/owlbear_kanban/migrate.py and serve/kanban/tests/test_migrate.py.
- Coverage: N/A for module percentage in this scoped run because the migrate CLI path executes in subprocess mode; functional AC evidence remains the fully passing TestFromAC suite.
- Evidence summary: AC-mapped migrate suite is fully green after the latest test-writer proof-strengthening cycle, including strict AC-C33 exact-value assertions and AC-C38a summary-item anchoring.

Post-task reflection:
- Problem faced: none in this cycle; implementation was already stable and this was a pure verification gate.
- Workaround applied: used canonical quality-runner scoped verification and avoided incidental edits.
- Pattern discovered: for subprocess-driven CLI tests, green functional assertions are the authoritative signal when in-process coverage cannot be collected.
- Time sink: none.
- Quality gap: none observed in the scoped migrate source and test slice.
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 71 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- VS Code diagnostics: no errors in `serve/kanban/src/owlbear_kanban/migrate.py`, `serve/kanban/tests/test_migrate.py`, or `serve/kanban/pyproject.toml`.

### Coverage
- `owlbear_kanban.migrate`: unavailable in scoped evidence. quality-runner reported `CoverageWarning: No data was collected` under subprocess/pytest-cov instrumentation. I did not treat that as a standalone failure.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-C31 | `serve/kanban/pyproject.toml:9`; `serve/kanban/tests/test_migrate.py:212` | Yes | COVERED |
| AC-C32 | `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, `:336`, `:827`, `:836`, `:845`, `:857` | Yes | COVERED |
| AC-C33 | Task and archive sub-contracts are well covered at `serve/kanban/tests/test_migrate.py:363`, `:375`, `:406`, `:430`, `:461`, `:494`, `:505`, `:521`, `:561`, `:573`, `:970`, `:985`, `:999`, `:1011`, `:1029`. But the latest Architecture Review makes config C4 require preserving `priorities` at `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1301`, while the approved tightening in `serve/kanban/tests/test_migrate.py:521-546` asserts only `entry_status`, `claim_timeout`, `next_id`, and `wave_size`. | No. A mutant changing `new_cfg["priorities"]` at `serve/kanban/src/owlbear_kanban/migrate.py:416` would still pass the current AC suite. | MISSING |
| AC-C34 | `serve/kanban/tests/test_migrate.py:605`, `:622` | Yes | COVERED |
| AC-C35 | `serve/kanban/tests/test_migrate.py:549`, `:584`, `:1109`, `:1127`, `:1162`, `:1244`, `:1274`, `:1303`; predicate at `serve/kanban/src/owlbear_kanban/migrate.py:155` | Yes | COVERED |
| AC-C36 | `serve/kanban/tests/test_migrate.py:641`, `:655`, `:682`, `:1365`, `:1378` | Yes | COVERED |
| AC-C37 | Live subprocess proof at `serve/kanban/tests/test_migrate.py:1408`, `:1418`, `:1431`, `:1444`, `:1462` | Yes | COVERED |
| AC-C38 | `serve/kanban/tests/test_migrate.py:759`, `:765`, `:775`, `:785`; exit path at `serve/kanban/src/owlbear_kanban/migrate.py:609` | Yes | COVERED |
| AC-C38a | `serve/kanban/tests/test_migrate.py:1516`, `:1524`, `:1530`, `:1536`, `:1544`, `:1552`, `:1580`, `:1597`, `:1624`, `:1642`; summary emission at `serve/kanban/src/owlbear_kanban/migrate.py:500-503`, `:602-606` | Yes | COVERED |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run on `serve/kanban/tests/test_migrate.py` | Yes | COVERED |

#### Security Review
- No issues found. The reviewed path remains a local CLI/file migration flow using argparse and YAML loaders, with atomic writes at `serve/kanban/src/owlbear_kanban/migrate.py:248`, `:318`, and `:456`. No shell, eval, network, or secret surface was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_*` suite in `serve/kanban/tests/test_migrate.py` | Current builder cycle touched no files; no weakened or removed assertions were detected in the current retry state. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most contracts are pinned exactly, but config C4 omits any assertion on migrated `priorities` despite latest task-body refinement requiring it. |
| Negative/error-path coverage | ADEQUATE | Archive invalid-reason/refs, config manual-action, dry-run, idempotency, and crash-resume paths are exercised. |
| Manual mutation reasoning | WEAK | Changing `new_cfg["priorities"]` at `serve/kanban/src/owlbear_kanban/migrate.py:416` to `[]` or any other value would still satisfy `serve/kanban/tests/test_migrate.py:521-546`; `grep` finds no `assert` against `priorities` anywhere in the test file. |
| Test independence | STRONG | Cases use isolated boards under `tmp_path`. |
| Descriptive names | STRONG | AC-tagged test names remain clear and specific. |

#### Data Safety
- No implementation-side data-safety issues found. Non-dry-run task, archive, and config writes still go through `atomic_write`, and the subprocess crash/resume suite remains the binding AC-C37 proof.

#### Implementation-Aware Gaps
- No scoped implementation defect found in `serve/kanban/src/owlbear_kanban/migrate.py`.
- The remaining blocker is proof quality for AC-C33 config C4. The task body says C4 must preserve `priorities` at `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1301`, and the completeness matrix claims that is proved at `:1401`, but the actual approved Change 7 omitted any priorities assertion and the resulting test still omits it at `serve/kanban/tests/test_migrate.py:521-546`.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 9 |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- I did not gate on the older parent-process crash tests at `serve/kanban/tests/test_migrate.py:709` and `:736`; the subprocess seam tests at `:1408-1499` carry the real AC-C37 proof.
- I did not gate on raw Brief §5.4 first-status wording for `entry_status`; the latest Architecture Review refinement in the task body is the binding authority for this looped task.

### Failing Findings
1. AC-C33 proof gap: config C4 still does not prove migrated `priorities` are preserved, even though the latest Architecture Review explicitly requires it. Evidence: `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1301`; `serve/kanban/src/owlbear_kanban/migrate.py:416`; `serve/kanban/tests/test_migrate.py:521-546`; no `assert` references `priorities` anywhere in `serve/kanban/tests/test_migrate.py`.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-C31 | Console script mapping exists at `serve/kanban/pyproject.toml:9` and is asserted at `serve/kanban/tests/test_migrate.py:212`. | `test_ac_c31_pyproject_scripts_exact_key_value` | PASS |
| AC-C32 | Lane routing and all-lane/exclusivity proofs at `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, `:336`, `:827`, `:836`, `:845`, `:857`. | `TestFromAC_LaneSelection`, `TestFromAC_LaneSelectionStrict` | PASS |
| AC-C33 | Task/archive proofs are present, but config C4 priorities preservation remains unproved against latest Architecture Review C4 at `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1301`. | `TestFromAC_LaneAlgorithms`, `TestFromAC_ArchiveLaneAlgorithmsStrict` | FAIL |
| AC-C34 | Idempotency counts pinned at `serve/kanban/tests/test_migrate.py:605`, `:622`. | `TestFromAC_Idempotency` | PASS |
| AC-C35 | Branch matrix and canonical-order checks at `serve/kanban/tests/test_migrate.py:549`, `:584`, `:1109`, `:1127`, `:1162`, `:1244`, `:1274`, `:1303`. | `TestFromAC_IdempotencyEdgeCases` | PASS |
| AC-C36 | Dry-run no-write and summary-label checks at `serve/kanban/tests/test_migrate.py:641`, `:655`, `:682`, `:1365`, `:1378`. | `TestFromAC_DryRun`, `TestFromAC_DryRunStrict` | PASS |
| AC-C37 | Subprocess crash/resume proof at `serve/kanban/tests/test_migrate.py:1408`, `:1418`, `:1431`, `:1444`, `:1462`. | `TestFromAC_CrashRecoverySubprocess` | PASS |
| AC-C38 | Exit-code and fail-line proof at `serve/kanban/tests/test_migrate.py:759`, `:765`, `:775`, `:785`. | `TestFromAC_ExitCode` | PASS |
| AC-C38a | Manual-action summary proofs at `serve/kanban/tests/test_migrate.py:1516`, `:1524`, `:1530`, `:1536`, `:1544`, `:1552`, `:1580`, `:1597`, `:1624`, `:1642`. | `TestFromAC_ManualActionSummaryStrict` | PASS |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run: 71 passed, 0 failed. | `serve/kanban/tests/test_migrate.py` | PASS |

### Deductions
- -0.08: AC-C33 config C4 priorities-preservation proof is missing.
- -0.04: manual mutation resistance is weak because a wrong `priorities` value in migrated config would still pass the current AC suite.

### Confidence: 0.88
### Verdict: FAIL -> backlog
### Action
- Tighten `test_ac_c33_config_lane_adds_new_required_fields` so it proves the migrated config preserves the legacy priorities list values, not just the other derived/preserved fields.
- Reconcile the task-body completeness claim at `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1401` with the actual approved Change 7, which currently omits the priorities assertion.
- No implementation fix is required in `serve/kanban/src/owlbear_kanban/migrate.py`; this rejection is on AC-proof completeness.
- Loop-breaker routing applies. The task file already contains prior `## Review Evidence` sections at `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:67`, `:169`, `:303`, `:502`, `:727`, `:950`, and `:1169`, so this reviewer rejection returns to `backlog`.

### Reflection
- Latest architecture refinements remain binding, but their completeness matrices still need direct verification against the actual tests.
- A single omitted preserved-value assertion can hide inside an otherwise green exact-value hardening cycle.
- For migration config tests, preserving a field and merely keeping the key present are different contracts.
- Subprocess-heavy CLI suites can be functionally strong while coverage remains unavailable; that instrumentation artifact should not distract from concrete proof gaps.

[[2026-04-24]]
## Architecture Review (cycle 6)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration entry point, one domain |
| Interface clarity | REFINE | AC-C33 C4 missing priorities assertion — single omission from cycle-5 guidance |
| Dependency correctness | PASS | #1052 and #1059 both archived |
| Module layering | PASS | `migrate.py` imports from `storage_io` and `body_parser` only |
| TDD compliance | PASS | 71 tests all pass, tagged `tdd:green` |
| KISS/YAGNI | PASS | Minimal scope — migration script only |
| Premise challenge | PASS | Migration script required for Brief C schema cutover |
| Pattern consistency | PASS | Uses `atomic_write`, `ruamel.yaml`, `argparse` — consistent |
| Security surface | PASS | YAML safe loader, atomic writes, no shell/eval/network |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: reconsider (0.66)
- Key concerns: (1) C1 statuses-conversion test only proves one status, not full list; (2) C3 presence checks incomplete; (3) history of overclaiming completeness
- Architect response: ACCEPTED IN PART on completeness-matrix honesty; REBUTTED on C1/C3 scope expansion:
  - **C1**: The test proves the *algorithm step* — dict-to-string shape conversion (`name: research` absent, `- research` present). Full-list preservation is a Python language guarantee (list comprehension iterates all elements). The reviewer did not challenge C1 across 8 cycles; opening it now is scope creep.
  - **C3**: Presence-checked fields (`entry_status`, `wave_size`, `non_impl_tags`, `archival_reasons`) cover the non-derived new fields. `claim_timeout`, `next_id`, and `wave_size` are value-checked (implies presence). `agent_map`, `agent_types`, `agent_compatibility`, `status_predicates` were explicitly excluded as C5 implementation constants in cycle 5. `priorities` is the one gap — it's a preserved field, not a presence-only field, and it IS the reviewer's finding.
  - **Completeness matrix**: Valid concern. The cycle-5 matrix overclaimed C4. This cycle's guidance corrects that by making the single fix explicit and verifiable.

### AC Refinement Applied

**AC-C33 C4** (revised): Derive `entry_status` from legacy `defaults.status`; preserve `claim_timeout`, `next_id`, `priorities` from legacy config. Exact-value proof required for all four preserved/derived fields:
  - `entry_status: research` → ✅ proved
  - `claim_timeout: 1h` → ✅ proved
  - `next_id: 1001` → ✅ proved
  - `wave_size: 4` → ✅ proved (constant, not preserved)
  - `priorities` list preserved from legacy → ❌ MISSING — add assertion

### Loop-Breaker Guidance (12th cycle — FINAL)

This task has cycled 8 times on proof-only gaps. Implementation is confirmed correct by ALL 8 reviews. Exactly 1 assertion is missing. The test-writer MUST add this 1 assertion and ONLY this 1 assertion:

**Fix 1** — TIGHTEN `test_ac_c33_config_lane_adds_new_required_fields` (line ~521)

After the existing `wave_size: 4` assertion block (line ~546), add:
```python
# AC-C33 (C4): priorities list must be preserved from legacy config
assert "- someday" in content, "priorities must be preserved from legacy config"
assert "- critical" in content, "priorities list must include all legacy values"
```

This proves the priorities list is preserved with at least the first and last legacy values (`someday`, `critical`), which is sufficient to catch a mutation that drops or replaces the list. The legacy fixture at `test_migrate.py:64-69` defines 5 priorities; the implementation at `migrate.py:416` copies them verbatim.

### Completeness Matrix (FINAL — for reviewer verification)

After Fix 1, ALL AC-C33 sub-contracts from the cycle-5 enumeration are either PROVED or EXCLUDED:

| Sub-contract | Status | Evidence |
|-------------|--------|----------|
| T1 claimed_by removal | ✅ proved | existing test |
| T2 per-field timestamp normalisation | ✅ proved | Change 2 (cycle 5) |
| T3 claimed_at normalisation | ✅ proved | Change 3 (cycle 5) |
| T4 all defaults with exact values | ✅ proved | Change 1 (cycle 5) |
| T5 preserve-if-present | ✅ proved | Change 4 (cycle 5) |
| T6 canonical order | ✅ proved | AC-C35 existing |
| A1 archival_reason auto-fill | ✅ proved | existing |
| A2 archival_refs exact auto-fill | ✅ proved | Change 5 (cycle 5) |
| A3 body verbatim exact | ✅ proved | Change 6 (cycle 5) |
| A4 invalid reason failure | ✅ proved | existing |
| A5 invalid refs failure | ✅ proved | existing |
| C1 statuses conversion | ✅ proved | shape transformation (dict→string) |
| C2 legacy field removal | ✅ proved | existing |
| C3 new field presence | ✅ proved | value checks imply presence |
| C4 derived/preserved values | ✅ after Fix 1 | priorities assertion closes last gap |
| C5 hard-coded stubs | EXCLUDED | implementation constants |
| C6 hard-coded lists | EXCLUDED | implementation constants |

### Verdict: REFINE → APPROVE
### Action Taken: Added priorities assertion to AC-C33 C4 loop-breaker guidance. Single tightening fix. Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: architect cycle-6 loop-breaker guidance (12th cycle FINAL) cited single missing assertion — AC-C33 C4 `priorities` preservation unproved despite all other C4 derived/preserved fields being asserted.
- Test file: `serve/kanban/tests/test_migrate.py` (71 tests total, 0 failed)
- Commit: `cd19dbc2` — "test: tighten AC-C33 C4 priorities preservation assertion (#1061, test-writer)"

### Change made (1 assertion tightening, no new tests)

| Test | Change |
|------|--------|
| `TestFromAC_LaneAlgorithms::test_ac_c33_config_lane_adds_new_required_fields` | Added: `assert "- someday" in content` and `assert "- critical" in content` after existing `wave_size: 4` block — proves priorities list is preserved from legacy config |

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (unchanged) |
| AC-C32 | COVERED (unchanged — all 6 cross-lane exclusivity directions proved) |
| AC-C33 | COVERED — all cycle-5 sub-contracts proved: T1✅ T2✅ T3✅ T4✅ T5✅ T6✅ A1✅ A2✅ A3✅ A4✅ A5✅ C1✅ C2✅ C3✅ C4✅ (now includes priorities preservation) C5/C6 EXCLUDED |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED (unchanged — all 5 branch-matrix variants proved) |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED (unchanged) |

### Execution
- pytest: 71 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean
- Tightened assertion passes because implementation at `migrate.py:416` already preserves priorities verbatim.
[[2026-04-24]]
## Builder Notes
- Files changed: none (verification-only builder cycle).
- Implementation status: existing `serve/kanban/src/owlbear_kanban/migrate.py` remains unchanged and aligned to AC-C31 through AC-C38a.
- Tests: `serve/kanban/tests/test_migrate.py` -> 71 passed, 0 failed, 0 skipped.
- Lint: `ruff` clean for `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- Coverage: subprocess-driven CLI execution yielded no direct module coverage data for `migrate.py`; functional AC evidence is the fully passing `TestFromAC_*` suite.
- Evidence summary: scoped quality-runner verification confirms the strict AC-proof suite remains green after latest test-writer tightening.

Post-task reflection:
- Problem faced: none in this cycle; this was a verification gate.
- Workaround applied: relied on scoped quality-runner evidence rather than incidental local reruns.
- Pattern discovered: subprocess-heavy CLI tests can validate behavior strongly while module coverage remains unavailable.
- Time sink: none.
- Quality gap: none observed in the scoped migrate source/test slice.
[[2026-04-24]]
## Review Evidence
### Test Results
- quality-runner scoped run on serve/kanban/tests/test_migrate.py: 71 passed, 0 failed, 0 skipped.

### Lint
- quality-runner: ruff clean on serve/kanban/src/owlbear_kanban/migrate.py and serve/kanban/tests/test_migrate.py.
- VS Code diagnostics: no errors in serve/kanban/src/owlbear_kanban/migrate.py, serve/kanban/tests/test_migrate.py, or serve/kanban/pyproject.toml.

### Coverage
- owlbear_kanban.migrate: unavailable in scoped evidence. quality-runner reported no data collected because the CLI suite executes the entry point in subprocesses. I did not treat that as a standalone failure.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Verdict |
|---------|----------|---------|
| AC-C31 | serve/kanban/pyproject.toml:9; serve/kanban/tests/test_migrate.py:212 | COVERED |
| AC-C32 | serve/kanban/tests/test_migrate.py:230, :245, :257, :285, :317, :336, :860 cover per-lane routing, all-lane processing, and exclusivity | COVERED |
| AC-C33 | Task and archive sub-contracts are well covered at serve/kanban/tests/test_migrate.py:375, :406, :430, :461, :564, :576, :1014. Config C4 is still under-proved: the latest Architecture Review still requires preserving priorities from legacy config at .owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1584, the implementation copies the whole list at serve/kanban/src/owlbear_kanban/migrate.py:416, but the AC-owned proof at serve/kanban/tests/test_migrate.py:549-550 asserts only the first and last values. A mutant that writes ["someday", "critical"] and drops the middle priorities would still pass. | MISSING |
| AC-C34 | serve/kanban/tests/test_migrate.py:608, :625 pin Migrated: 0 on rerun and modern-board input | COVERED |
| AC-C35 | serve/kanban/tests/test_migrate.py:1130, :1165, :1247, :1277, :1306 with predicate at serve/kanban/src/owlbear_kanban/migrate.py:155 | COVERED |
| AC-C36 | serve/kanban/tests/test_migrate.py:644, :658, :1368 prove no-write behavior across task, config, and archive lanes | COVERED |
| AC-C37 | serve/kanban/tests/test_migrate.py:1411, :1421, :1434, :1447, :1465 prove crash, no partial temp files, resume, and full-content convergence | COVERED |
| AC-C38 | serve/kanban/tests/test_migrate.py:762, :768, :778 prove success/failure exit codes and FAIL stderr lines | COVERED |
| AC-C38a | serve/kanban/tests/test_migrate.py:1519, :1555, :1600, :1645 with archive/config manual-action collation at serve/kanban/src/owlbear_kanban/migrate.py:503, :537 and summary emission at :602 | COVERED |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run on serve/kanban/tests/test_migrate.py | COVERED |

#### Security Review
- No issues found. The reviewed path remains a local CLI and file-migration flow using safe or round-trip YAML loaders plus atomic writes. No shell, network, eval, or secret surface was introduced.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| TestFromAC suite in serve/kanban/tests/test_migrate.py | Latest retry tightened assertions only; no weakened or removed TestFromAC assertions detected. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | ADEQUATE | Most contracts are pinned exactly, but config priorities preservation is represented only by two sentinel values. |
| Negative or error-path coverage | ADEQUATE | Archive invalid-reason and invalid-refs cases, config manual-action paths, dry-run, idempotency, and crash-resume paths are exercised. |
| Manual mutation reasoning | WEAK | serve/kanban/src/owlbear_kanban/migrate.py:416 copies the full legacy priorities list, but serve/kanban/tests/test_migrate.py:549-550 assert only "- someday" and "- critical". Dropping the middle legacy priorities would still satisfy the suite while violating C4 preservation. |
| Test independence | STRONG | Cases build isolated boards under tmp_path. |
| Descriptive names | STRONG | AC-tagged names remain clear and specific. |

#### Data Safety
- No implementation-side data-safety issues found. Non-dry-run writes still go through atomic_write, and the subprocess crash-resume suite remains the binding proof for partial-failure recovery.

#### Implementation-Aware Gaps
- No scoped implementation defect found in serve/kanban/src/owlbear_kanban/migrate.py.
- The remaining blocker is proof quality for AC-C33 config C4. The latest Architecture Review says preserve priorities from legacy config at .owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1584, but the approved assertion block at :1599-1601 and the resulting test at serve/kanban/tests/test_migrate.py:549-550 only pin the first and last values.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Assessment | FRICTION |
| Evidence | This task is well past the third review cycle. Loop-breaker routing applies regardless of the latest builder cycle being verification-only. Prior Review Evidence sections already exist at .owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:67, :169, :303, :502, :727, :950, :1169, and :1461. |

### Failing Findings
1. AC-C33 proof gap: config C4 still does not prove that the migrated priorities list is preserved from the legacy config. Evidence: .owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1584, serve/kanban/src/owlbear_kanban/migrate.py:416, and serve/kanban/tests/test_migrate.py:549-550. A mutant that writes only ["someday", "critical"] or otherwise drops the middle legacy priorities would still pass.

### AC Compliance
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | serve/kanban/pyproject.toml:9; serve/kanban/tests/test_migrate.py:212 | PASS |
| AC-C32 | serve/kanban/tests/test_migrate.py:230, :245, :257, :285, :317, :336, :860 | PASS |
| AC-C33 | Config C4 priorities preservation remains under-proved against the latest Architecture Review at .owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1584 | FAIL |
| AC-C34 | serve/kanban/tests/test_migrate.py:608, :625 | PASS |
| AC-C35 | serve/kanban/tests/test_migrate.py:1130, :1165, :1247, :1277, :1306; serve/kanban/src/owlbear_kanban/migrate.py:155 | PASS |
| AC-C36 | serve/kanban/tests/test_migrate.py:644, :658, :1368 | PASS |
| AC-C37 | serve/kanban/tests/test_migrate.py:1411, :1421, :1434, :1447, :1465 | PASS |
| AC-C38 | serve/kanban/tests/test_migrate.py:762, :768, :778 | PASS |
| AC-C38a | serve/kanban/tests/test_migrate.py:1519, :1555, :1600, :1645; serve/kanban/src/owlbear_kanban/migrate.py:503, :537, :602 | PASS |
| All RED tests from C-07 (#1052) pass | quality-runner scoped run: 71 passed, 0 failed | PASS |

### Deductions
- -0.08: AC-C33 config priorities-preservation proof is still incomplete.
- -0.04: Manual mutation resistance is weak because the current suite would still pass after dropping middle legacy priorities.

### Confidence
- 0.88

### Verdict
- FAIL. Move to backlog.

### Action
- Tighten TestFromAC_LaneAlgorithms::test_ac_c33_config_lane_adds_new_required_fields so it proves the whole migrated priorities list matches the legacy list, not just first and last sentinel values.
- Reconcile the latest architecture loop-breaker guidance at .owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1599-1601 with the actual C4 contract at :1584; the current guidance under-proves the required preservation behaviour.
- No implementation fix is required in serve/kanban/src/owlbear_kanban/migrate.py; this rejection is on AC-proof completeness.

### Reflection
- Loop-breaker guidance can still under-prove a preserved-list contract even when it closes the previously reported missing-field case.
- On config migrations, sentinel-value assertions are not equivalent to list preservation.
- A green subprocess-heavy CLI suite still needs mutation-resistant content assertions when direct module coverage is unavailable.
[[2026-04-24]]
## Architecture Review (cycle 7)

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One migration entry point, one domain |
| Interface clarity | REFINE | AC-C33 C4 priorities assertion too weak (sentinel-only) — final fix below |
| Dependency correctness | PASS | #1052 and #1059 both archived |
| Module layering | PASS | `migrate.py` imports from `storage_io` and `body_parser` only |
| TDD compliance | PASS | 71 tests all pass, tagged `tdd:green` |
| KISS/YAGNI | PASS | Minimal scope — migration script only |
| Premise challenge | PASS | Migration script required for Brief C schema cutover |
| Pattern consistency | PASS | Uses `atomic_write`, `ruamel.yaml`, `argparse` — consistent |
| Security surface | PASS | YAML safe loader, atomic writes, no shell/eval/network |
| Single domain | PASS | Kanban domain only |

### Challenge Results
- Challenger: FALLBACK — runSubagent error
- Architect response: proceeding with independent evaluation

### AC Refinement Applied

**AC-C33 C4** (revised): priorities assertion must check ALL 5 legacy values, not just first/last sentinels. The implementation at `migrate.py:416` copies the entire list via `plain_raw.get("priorities", [])`. The legacy fixture defines: someday, nice-to-have, important, needed, critical. A mutant writing `["someday", "critical"]` (dropping middle 3) would pass the current sentinel-only assertions.

### SCOPE LOCK — AC-C33 sub-contract enumeration is CLOSED

The cycle-5 AC-C33 sub-contract enumeration (T1–T6, A1–A5, C1–C6) is the authoritative and complete list. The reviewer must evaluate ONLY against these enumerated sub-contracts. No new sub-contracts may be inferred from Brief §5.3/§5.4 or the implementation.

Rationale: "match exactly" is infinitely divisible — this is the root cause of 9 review cycles on a correct implementation. The sub-contracts were enumerated in cycle 5 after comprehensive Brief analysis. Each subsequent cycle has only tightened existing items, not discovered genuinely new algorithm steps.

Specifically EXCLUDED from further reviewer expansion:
- C1 full-list verification (shape conversion proved; list iteration is a language guarantee)
- C5/C6 hard-coded implementation constants
- `parse_body` dead-branch testing (excluded in cycle 3 with source evidence)
- Any sub-contract not listed in the cycle-5 enumeration

### Loop-Breaker Guidance (14th cycle — FINAL)

This task has cycled 9 times on proof-only gaps. Implementation confirmed correct by ALL 9 reviews. Exactly 1 assertion tightening is needed. The test-writer MUST make this 1 change and ONLY this 1 change:

**Fix 1** — TIGHTEN `test_ac_c33_config_lane_adds_new_required_fields` (line ~548-550)

Replace the sentinel-only assertions:
```python
# AC-C33 (C4): priorities list must be preserved from legacy config
assert "- someday" in content, "priorities must be preserved from legacy config"
assert "- critical" in content, "priorities list must include all legacy values"
```

With full-list assertions:
```python
# AC-C33 (C4): priorities list must be preserved from legacy config (all 5 values)
for p in ("someday", "nice-to-have", "important", "needed", "critical"):
    assert f"- {p}" in content, f"priorities must include '{p}' from legacy config"
```

This proves the full 5-item list is preserved, catching any mutant that drops middle values. The loop pattern matches the legacy fixture at `test_migrate.py:64-69`.

### Completeness Matrix (FINAL — scope-locked)

| Sub-contract | Status |
|-------------|--------|
| T1 claimed_by removal | ✅ proved |
| T2 per-field timestamp normalisation | ✅ proved |
| T3 claimed_at normalisation | ✅ proved |
| T4 all defaults with exact values | ✅ proved |
| T5 preserve-if-present | ✅ proved |
| T6 canonical order | ✅ proved |
| A1 archival_reason auto-fill | ✅ proved |
| A2 archival_refs exact auto-fill | ✅ proved |
| A3 body verbatim exact | ✅ proved |
| A4 invalid reason failure | ✅ proved |
| A5 invalid refs failure | ✅ proved |
| C1 statuses conversion | ✅ proved (shape) |
| C2 legacy field removal | ✅ proved |
| C3 new field presence | ✅ proved |
| C4 derived/preserved values | ✅ after Fix 1 |
| C5 hard-coded stubs | EXCLUDED |
| C6 hard-coded lists | EXCLUDED |

### Verdict: REFINE → APPROVE
### Action Taken: Tightened AC-C33 C4 priorities guidance to require full 5-value assertion. Added scope lock on AC-C33 sub-contract enumeration to prevent further expansion. Advanced to todo.
[[2026-04-24]]
## Test-Writer Notes
- Retry cycle: architect cycle-7 loop-breaker guidance (14th cycle FINAL) — single assertion tightening on AC-C33 C4 priorities preservation.
- Test file: `serve/kanban/tests/test_migrate.py` (71 tests total, 0 failed)
- Commit: `5da4cbef` — "test: tighten AC-C33 C4 priorities full-list assertion (#1061, test-writer)"

### Change made (1 assertion tightening, no new tests)

| Test | Change |
|------|--------|
| `TestFromAC_LaneAlgorithms::test_ac_c33_config_lane_adds_new_required_fields` | Replaced sentinel-only `- someday`/`- critical` checks with a loop asserting all 5 legacy priority values (`someday`, `nice-to-have`, `important`, `needed`, `critical`) — catches any mutant dropping middle values |

### AC coverage

| AC | Status |
|----|--------|
| AC-C31 | COVERED (unchanged) |
| AC-C32 | COVERED (unchanged — all 6 cross-lane exclusivity directions proved) |
| AC-C33 | COVERED — all cycle-5 sub-contracts: T1✅ T2✅ T3✅ T4✅ T5✅ T6✅ A1✅ A2✅ A3✅ A4✅ A5✅ C1✅ C2✅ C3✅ C4✅ (priorities full-list now proved) C5/C6 EXCLUDED |
| AC-C34 | COVERED (unchanged) |
| AC-C35 | COVERED (unchanged — all 5 branch-matrix variants proved) |
| AC-C36 | COVERED (unchanged) |
| AC-C37 | COVERED (unchanged) |
| AC-C38 | COVERED (unchanged) |
| AC-C38a | COVERED (unchanged) |

### Execution
- pytest: 71 passed, 0 failed (`serve/kanban/tests/test_migrate.py`)
- ruff: clean

[[2026-04-24]]
## Builder Notes
- Files changed: none (verification-only builder cycle).
- Implementation status: existing `serve/kanban/src/owlbear_kanban/migrate.py` remains unchanged and aligned to AC-C31 through AC-C38a.
- Tests: `uv run pytest serve/kanban/tests/test_migrate.py -q --tb=short` -> 71 passed, 0 failed.
- Lint: `uv run ruff check serve/kanban/src/owlbear_kanban/migrate.py serve/kanban/tests/test_migrate.py` -> clean.
- Coverage: not re-measured in this scoped close; known subprocess-driven CLI execution can report no-data for module coverage.
- Evidence summary: full migrate AC suite remains green, including strict AC-C33 and AC-C38a proof assertions.

Post-task reflection:
- Problem faced: none in this cycle; task functioned as a verification gate.
- Workaround applied: used a strict scoped verification run and avoided incidental edits.
- Pattern discovered: verification-only builder closes are appropriate when implementation is stable and AC-proof tests are already hardened.
- Time sink: none.
- Quality gap: none observed in the scoped migrate module/test slice.
[[2026-04-24]]
## Review Evidence

### Test Results
- Independent quality-runner scoped run on `serve/kanban/tests/test_migrate.py`: 71 passed, 0 failed, 0 skipped.
- I did not rely on builder self-reports; the pass/fail decision is based on the independent run above.

### Lint
- Independent quality-runner lint: clean on `serve/kanban/src/owlbear_kanban/migrate.py` and `serve/kanban/tests/test_migrate.py`.
- VS Code diagnostics: no errors in `serve/kanban/src/owlbear_kanban/migrate.py`, `serve/kanban/tests/test_migrate.py`, or `serve/kanban/pyproject.toml`.

### Coverage
- Module coverage is unavailable in scoped evidence because the suite executes `python -m owlbear_kanban.migrate` in subprocesses; quality-runner reported `unable_to_measure` / `no data collected`.
- I did not treat that as a separate failure. The task uses black-box CLI tests, and the recovery primitive is also covered directly in `serve/kanban/tests/test_storage_io.py:202`.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | Console-script mapping exists at `serve/kanban/pyproject.toml:9`; exact proof at `serve/kanban/tests/test_migrate.py:212`. | PASS |
| AC-C32 | Per-lane routing, all-lane processing, and all six exclusivity directions are proved at `serve/kanban/tests/test_migrate.py:230`, `:245`, `:257`, `:285`, `:317`, and `:336`. | PASS |
| AC-C33 | Current binding scope is the latest Architecture Review at `.owlbear/kanban/tasks/1061-c-16-green-kanban-migrate-entry-point.md:1771` with scope lock at `:1795`. The enumerated sub-contracts are covered by exact-value and branch tests at `serve/kanban/tests/test_migrate.py:375`, `:406`, `:430`, `:461`, `:521`, `:564`, `:576`, and `:1014`; config priorities are copied at `serve/kanban/src/owlbear_kanban/migrate.py:416` and now proved by the full 5-value assertion loop in the AC-owned config test at `serve/kanban/tests/test_migrate.py:521`. | PASS |
| AC-C34 | Idempotency counts pinned at `serve/kanban/tests/test_migrate.py:605` and `:622`. | PASS |
| AC-C35 | Branch-matrix proofs for missing task timestamps, invalid archive refs (non-list and boolean-list), and non-canonical task order exist at `serve/kanban/tests/test_migrate.py:1130`, `:1165`, `:1247`, `:1277`, and `:1306`; predicate at `serve/kanban/src/owlbear_kanban/migrate.py:155`. | PASS |
| AC-C36 | No-write behavior is proved across task, config, and archive dry runs at `serve/kanban/tests/test_migrate.py:644`, `:658`, and `:1368`. | PASS |
| AC-C37 | Crash/resume behavior is proved at the subprocess seam at `serve/kanban/tests/test_migrate.py:1411` and `:1465`; writes remain atomic at `serve/kanban/src/owlbear_kanban/migrate.py:248`, `:318`, and `:456`. | PASS |
| AC-C38 | Exit-code and fail-line behavior are proved at `serve/kanban/tests/test_migrate.py:768` and `:778`; runtime paths at `serve/kanban/src/owlbear_kanban/migrate.py:501` and `:609`. | PASS |
| AC-C38a | Config rerun and archive manual-action summary proofs are present at `serve/kanban/tests/test_migrate.py:1555`, `:1600`, and `:1645`; summary items and summary block are emitted from `serve/kanban/src/owlbear_kanban/migrate.py:503`, `:537`, and `:602`. | PASS |
| All RED tests from C-07 (#1052) pass | Independent quality-runner scoped run on `serve/kanban/tests/test_migrate.py`. | PASS |

#### Security Review
- No security issues found in the reviewed scope.
- The entry point is a local file-migration CLI with argparse-constrained lane selection, safe/round-trip YAML loaders, and atomic writes. No shell, network, eval, or secret surface was introduced.

#### Test Integrity
- No weakened or removed `TestFromAC_*` assertions detected in the current state.
- The latest retry tightened the AC-C33 C4 priorities proof in-place; it did not relax earlier AC assertions.

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Exact script mapping, exact task defaults, per-field timestamp checks, exact archive body equality, and anchored summary-item assertions are present in the live suite. |
| Negative/error-path coverage | STRONG | Invalid archive reason/refs, config rerun with unresolved stubs, missing task timestamps, dry-run, exit-1, and crash/resume paths are all exercised. |
| Manual mutation reasoning | ADEQUATE | Within the latest scope-locked AC-C33 sub-contract set, the current suite would fail on the previously identified priorities-drop mutant because the config test now asserts all 5 legacy priority values. |
| Test independence | STRONG | Cases build isolated boards under `tmp_path`; no shared mutable state was observed. |
| Descriptive names | STRONG | AC-tagged names remain clear and specific. |

#### Data Safety
- No data-safety issues found.
- Task, archive, and config writes still route through `atomic_write` at `serve/kanban/src/owlbear_kanban/migrate.py:248`, `:318`, and `:456`.

#### Implementation-Aware Gaps
- No scoped implementation defect found in `serve/kanban/src/owlbear_kanban/migrate.py`.
- No remaining AC-proof gap found in `serve/kanban/tests/test_migrate.py` after the latest priorities full-list tightening.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 11 |
| Review Evidence sections in history | 8 prior FAIL sections before this pass cycle |
| Approach variation | Yes |
| Assessment | FRICTION |

### Pass 2 — INFORMATIONAL
- The older parent-process `os.replace` monkeypatch tests remain non-binding; the subprocess crash suite carries the real AC-C37 proof.
- Coverage remained unavailable for the known subprocess architecture reason and was not treated as a standalone failure.

### Deductions
- None.

### Verdict
- PASS -> docs
- Confidence: 0.95

### Action
- Advance to docs. The implementation and AC-owned proof suite now satisfy the current, scope-locked task contract.

### Reflection
- On looped review tasks, the latest Architecture Review refinement must govern; stale older FAIL sections are not authoritative once the named gap is closed.
- Subprocess-heavy CLI suites can justify unavailable module coverage when the behavioral assertions are explicit and mutation-resistant.
- The final AC-C33 blocker was proof completeness only; the implementation remained stable throughout the later cycles.
[[2026-04-24]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | Verified / N/A | `serve/kanban/README.md` Migration section accurately reflects `kanban-migrate` — command syntax, all flags (`--lane`, `--dry-run`, `--kanban-dir`), exit codes, and agent_map/types/compat stub note match `migrate.py:546-616`. No update needed. |
| 2 | Module docstrings | Yes | Verified / N/A | Module docstring (`migrate.py:1-9`) and `main()` docstring (`:547`) are accurate. All other functions are private (`_` prefix) — not public API. |
| 3 | External attribution | No | N/A | No external patterns used; no sources row needed. |
| 4 | Research doc | No | N/A | No research doc referenced in task body. |
| 5 | Diagram maintenance (describes match) | Yes | Verified / N/A | `share/diagrams/kanban.excalidraw` and `share/diagrams/mcp-topology.excalidraw` both describe `serve/kanban/src/**`. Both footers already show `Last verified: 2026-04-24 (cf0325cf)` in HEAD — current. No update needed. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. No orphaned docs detected. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/migrate.py` | IN (docstrings) | Verified — accurate |
| `serve/kanban/tests/test_migrate.py` | OUT | N/A |
| `serve/kanban/pyproject.toml` | OUT | N/A |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-04-24]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-C31 | `serve/kanban/pyproject.toml:9` exact mapping; `test_migrate.py:212` assertion | PASS |
| AC-C32 | 7 lane-routing + exclusivity tests; reviewer verified all 6 cross-lane directions | PASS |
| AC-C33 | 17 enumerated sub-contracts (T1–T6, A1–A5, C1–C6) with scope lock; spot-checked C4 priorities — all 5 legacy values asserted in loop | PASS |
| AC-C34 | `test_migrate.py:605`, `:622` pin `Migrated: 0` | PASS |
| AC-C35 | 5 branch-matrix variants proved (archive non-list refs, boolean-list refs, missing created/updated, non-canonical order) | PASS |
| AC-C36 | Dry-run no-write assertions present | PASS |
| AC-C37 | Subprocess crash-resume proof at `:1411–1465` | PASS |
| AC-C38 | Exit-code and FAIL-line assertions at `:762–778` | PASS |
| AC-C38a | Spot-checked: `- archive:` summary-item assertions anchor path AND reason text for both invalid-reason and invalid-refs | PASS |
| All RED tests from C-07 (#1052) pass | quality-runner: 71 passed, 0 failed | PASS |

### Test Results
- pytest (task-scoped): 71 passed, 0 failed, 0 skipped
- pytest (full suite): 1680 passed, 73 failed — 0 failures in `test_migrate.py`; all 73 are pre-existing failures in other test files (`test_yaml12_loader_940.py`, `test_list_sessions.py`, `test_engine_init_1067.py`, `test_storage.py`)
- ruff: clean on `migrate.py` and `test_migrate.py`

### Architect Quality: 3/5
Original AC-C33 "match §5.3/§5.4 exactly" was vague and infinitely divisible — root cause of a 9-review-cycle loop on a correct implementation. The architect eventually produced strong refinements (17 enumerated sub-contracts, scope lock, detailed loop-breaker guidance with exact test specs), but the initial AC quality caused significant pipeline waste. AC-C35 and AC-C38a also required multiple refinement cycles to specify branch matrices.

### Deduction Breakdown
- AC quality score ≤ 3: -0.03
- No other deductions: all AC lines have specific evidence, lint clean, reviewer evidence present and detailed, no task-scoped test failures

### Confidence: 0.97
### Action: archive