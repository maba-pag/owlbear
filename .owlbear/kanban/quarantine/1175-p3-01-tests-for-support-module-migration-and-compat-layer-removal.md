---
id: 1175
title: 'P3-01: Tests for support module migration and compat layer removal'
status: archived
priority: nice-to-have
created: 2026-04-29T07:36:11.999957+00:00
updated: 2026-04-30T00:38:09.361597+00:00
tags:
- scope:kanban
- phase-3
- type:test
parent: 1155
depends_on:
- 1174
blocked: false
block_reason: 'test-writer crashed twice: GitHub service disruption (no response returned)'
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Parent: #1155 — config.yml schema grouping (nested sub-models)
Phase 3 of 3: Support Modules + Cleanup — test task
Depends on: #1174 (engine migration complete)

## Acceptance Criteria

- [ ] Tests validate corruption.py uses sub-model access paths for all 8 identified access sites (td:1)
- [ ] Tests validate storage.py non-save_config sites use sub-model access paths for all 9 identified sites (td:1)
- [ ] Tests verify BoardConfig no longer exposes forwarding properties (compat layer removed) (td:1)
- [ ] Tests verify live config.yml loads via canonical `load_config()` with value-equality assertions proving grouped extraction: `config.pipeline.statuses` must equal the root statuses list (non-empty; PipelineConfig default is `[]`) — type-only assertions are insufficient (td:1)
- [ ] Tests verify terminal_status present in live config (td:1)

## Scope

- In: corruption.py test coverage, storage.py test coverage (non-save_config), compat removal tests, live config validation
- Out: engine.py (done in Phase 2), sub-model definitions (done in Phase 1)
[[2026-04-29]]

[[2026-04-29]]

## Test-Writer Notes (prior cycles)

- Test file: tests/test_support_migration_1175.py
- Classes: TestFromAC_CorruptionSubModelPaths, TestFromAC_StorageNonSaveConfigPaths, TestFromAC_CompatLayerRemoval, TestFromAC_LiveConfigGroupedFormat, TestFromAC_LiveConfigTerminalStatus
- Total: 40 tests (39 original + 1 retry), all PASS
- AC4 gap: the retry test at `test_live_config_loads_via_canonical_loader_with_grouped_submodels` uses type-only isinstance assertions — these must be replaced with value-equality assertions per refined AC4

## Review History Summary

- Review 1: FAIL on AC4 — test never hit canonical loader path. Fixed in retry.
- Review 2: FAIL on AC4 — retry hit loader but used type-only assertions; live values match model defaults so type checks don't prove extraction.
- Root cause: AC4 was ambiguous about proof strength. Now refined.

## Architecture Review

**Verdict:** REFINE → approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: corruption.py sub-model access paths | Verifiable, 2 prior reviews PASS | No change (td:1) |
| AC2: storage.py non-save_config sub-model paths | Verifiable, 2 prior reviews PASS | No change (td:1) |
| AC3: BoardConfig no forwarding properties | Verifiable, 2 prior reviews PASS | No change (td:1) |
| AC4: live config loads in grouped format | **Ambiguous proof requirement** — caused 2 review failures | Refined (td:1) |
| AC5: terminal_status in live config | Verifiable, 2 prior reviews PASS | No change (td:1) |

### AC4 Refinement Rationale

The live config's grouped sub-model values (`paths.tasks_dir="tasks"`, `pipeline.terminal_status="done"`, etc.) all match Pydantic model defaults. Type-only assertions cannot distinguish extraction from defaulting. However:

- `PipelineConfig.statuses` defaults to `[]`
- The normalizer at `serve/kanban/src/owlbear_kanban/models.py:305-310` populates `config.pipeline.statuses` from root `statuses` via `setdefault()`
- Asserting `config.pipeline.statuses` is non-empty and equals the root statuses list proves extraction

### Architecture Notes

- Adjacent precedent: `tests/test_config_schema_1171.py:314-322` uses nondefault values for extraction proof
- No new interfaces, dependencies, or security surface
- Task is `type:test` — test-writer pass-through expected, builder adjusts the existing test

### Loop-Breaker Resolution

Two prior review failures on AC4 traced to ambiguous AC text. Refined AC4 provides an unambiguous proof target (`config.pipeline.statuses` equality). No further cycles expected.

### Test-Writer Guidance

Replace isinstance assertions in `test_live_config_loads_via_canonical_loader_with_grouped_submodels` with:

```python
assert config.pipeline.statuses == config.statuses  # non-empty, proves normalizer extraction
assert len(config.pipeline.statuses) == 7  # PipelineConfig default is []
```

[[2026-04-29]]
REFINE → approve. AC4 refined from ambiguous "loads correctly in grouped format" to precise extraction-proof requirement (assert config.pipeline.statuses equals root statuses list; PipelineConfig default is [] so non-empty result proves extraction). Root cause of 2 prior review failures was ambiguous AC, not implementation or test-writer error. All td:1.
[[2026-04-29]]

## Test-Writer Notes

- Retry: replaced isinstance assertions in `test_live_config_loads_via_canonical_loader_with_grouped_submodels` with value-equality assertions per refined AC4.
- New assertions: `config.pipeline.statuses == config.statuses` and `len(config.pipeline.statuses) == 7`
- All 40 tests PASS against current implementation — normalizer extraction is already correct.
- Builder skip: test-only retry, all tests green (Step 1b.1).
- AC4 proof-strength gap resolved: isinstance checks replaced with equality checks that prove normalizer extraction (PipelineConfig.statuses defaults to [] — non-empty equality result proves extraction happened).
- Lint: clean (ruff exit 0)
[[2026-04-29]]
Builder skip: test-only retry per Step 1b.1. Test file `tests/test_support_migration_1175.py` updated with value-equality assertions — all 40 tests green. No source changes needed.
[[2026-04-29]]

## Review Evidence

### Changed Scope

- Reviewed task-owned retry only: `tests/test_support_migration_1175.py` (builder skip; no source diff noted in task body)

### Test Results

- pytest: 40 passed, 0 failed, 0 skipped (`quality-runner`, scoped to `tests/test_support_migration_1175.py`)

### Lint

- ruff: clean (`quality-runner`, scoped to `tests/test_support_migration_1175.py`)

### Coverage

- N/A for gate: td:1 review and this retry changed only the task-owned test file, not source modules.

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: corruption.py uses sub-model access paths for all 8 identified access sites | `TestFromAC_CorruptionSubModelPaths` | No. `_PathsConfig` keeps default `tasks/archive` values (`tests/test_support_migration_1175.py:38-39`), and runtime checks at `:216`, `:233`, `:251` never override them. A mutation hardcoding `"archive"` at `corruption.py:587` while leaving `_is_archive_path()` at `corruption.py:675` unchanged would still satisfy the module-wide positive source check at `tests/test_support_migration_1175.py:207` and still pass the runtime tests. | LAX |
| AC2: storage.py non-save_config sites use sub-model access paths for all 9 identified sites | `TestFromAC_StorageNonSaveConfigPaths` | No. `write_task()` is only checked for absence of `config.tasks_dir` at `tests/test_support_migration_1175.py:298`; it does not assert the actual sub-model access used at `storage.py:415`. `write_task_if_unchanged()` only checks absence of forwarding props at `:307` and `:317`; it does not prove the accesses at `storage.py:479-480`. Runtime checks at `:363`, `:380`, `:397` also use default `tasks/archive` values from `:38-39`, so hardcoded literal directories would still pass. | LAX |
| AC3: BoardConfig no longer exposes forwarding properties | `TestFromAC_CompatLayerRemoval` | Yes. Direct `BoardConfig.__dict__` property assertions at `tests/test_support_migration_1175.py:436-537` fail if any compat property exists; current `BoardConfig` block exposes only `status_names` as a property (`serve/kanban/src/owlbear_kanban/models.py:395`). | COVERED |
| AC4: live config loads via canonical `load_config()` with value-equality proof | `TestFromAC_LiveConfigGroupedFormat` | Yes. The retry now exercises `owbear_kanban.config_loader.load_config` and asserts exact equality `config.pipeline.statuses == config.statuses` plus `len(...) == 7` at `tests/test_support_migration_1175.py:607-623`, matching the grouped normalizer behavior in `serve/kanban/src/owlbear_kanban/models.py:300-318` and loader entry point at `serve/kanban/src/owlbear_kanban/config_loader.py:25-35`. | COVERED |
| AC5: terminal_status present in live config | `TestFromAC_LiveConfigTerminalStatus` | Yes. Raw YAML assertions at `tests/test_support_migration_1175.py:646-677` fail if `pipeline.terminal_status` is absent or not equal to the final live status; current live config defines it explicitly in `.owlbear/kanban/config.yml:16-20`. | COVERED |

#### Security Review

- No issues. The retry is test-only and adds no runtime input surface, persistence path, dependency, or secret handling.

#### Test Integrity

- No builder-authored weakening detected. The current AC4 retry strengthened the prior type-only check to exact value-equality, which is the correct direction.

#### Test Quality

- Assertion specificity: WEAK for AC1/AC2. Current tests mostly prove “not forwarding properties” but do not bind each site to actual `config.paths.*` usage.
- Negative/error-path coverage: ADEQUATE for task scope.
- Manual mutation reasoning: WEAK. Replacing `config.paths.tasks_dir` / `config.paths.archive_dir` with hardcoded default literals in multiple sites would still leave the suite green.
- Test independence: STRONG.
- Descriptive names: STRONG.

#### Data Safety

- No issues.

#### Implementation-Aware Gaps

- No source defect found in the current implementation. `corruption.py` currently uses `config.paths.tasks_dir` / `config.paths.archive_dir` at `:586-587,675`; `storage.py` currently uses `config.paths.tasks_dir` / `config.paths.archive_dir` at `:415,479-480,507,523,546-547`. The failure is proof strength in the tests, not implementation correctness.

#### Builder Process Quality

- Third review cycle on this task. Prior two fails were AC4 proof issues; this cycle found a separate AC1/AC2 false-green risk. Loop-breaker routing applies.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | Defaults-only runtime checks (`tests/test_support_migration_1175.py:38-39,216-287`) + module-wide positive string check (`:207`) do not prove every corruption.py site reads config paths; current source sites are `corruption.py:586-587,675` | `TestFromAC_CorruptionSubModelPaths` | FAIL |
| AC2 | `write_task` / `write_task_if_unchanged` tests (`tests/test_support_migration_1175.py:298-326`) only ban forwarding props and never assert the concrete sub-model accesses at `storage.py:415,479-480`; runtime checks (`:363-414`) use default path names and can false-green hardcoded literals | `TestFromAC_StorageNonSaveConfigPaths` | FAIL |
| AC3 | `tests/test_support_migration_1175.py:436-537`; `serve/kanban/src/owlbear_kanban/models.py:181-405` | `TestFromAC_CompatLayerRemoval` | PASS |
| AC4 | `tests/test_support_migration_1175.py:607-623`; `serve/kanban/src/owlbear_kanban/config_loader.py:25-35`; `serve/kanban/src/owlbear_kanban/models.py:300-318` | `TestFromAC_LiveConfigGroupedFormat` | PASS |
| AC5 | `tests/test_support_migration_1175.py:646-677`; `.owlbear/kanban/config.yml:16-20` | `TestFromAC_LiveConfigTerminalStatus` | PASS |

### Deductions

- -0.18: AC1 proof is lax against partial hardcoded-path mutations.
- -0.20: AC2 proof is lax against hardcoded default path literals and missing positive assertions for `write_task()` / `write_task_if_unchanged()`.
- Confidence: 0.72

### Verdict

- FAIL -> backlog

### Required Follow-up

- Tighten AC1/AC2 tests to use non-default sentinel path values for `config.paths.tasks_dir` / `config.paths.archive_dir` so hardcoded `"tasks"` / `"archive"` cannot pass.
- Add positive per-function assertions for `write_task()` and `write_task_if_unchanged()` that bind the implementation to `config.paths.tasks_dir` / `config.paths.archive_dir`, not just the absence of legacy forwarding-property access.
- Re-run scoped pytest + ruff after those proof-strength fixes.
[[2026-04-29]]

## Architecture Review (Cycle 2)

**Verdict:** REFINE → approve

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1: corruption.py sub-model access paths | Reviewer FAIL: default-value fixture allows false-green | Refined — require sentinel values (td:1) |
| AC2: storage.py non-save_config sub-model paths | Reviewer FAIL: default-value fixture allows false-green | Refined — require sentinel values (td:1) |
| AC3: BoardConfig no forwarding properties | PASS in 3 prior reviews | No change (td:1) |
| AC4: live config loads with value-equality proof | PASS after AC4 refinement | No change (td:1) |
| AC5: terminal_status in live config | PASS in 3 prior reviews | No change (td:1) |

### AC1/AC2 Refinement

**Root cause:** Test fixtures `_PathsConfig(tasks_dir="tasks", archive_dir="archive")` use values identical to `PathsConfig` Pydantic defaults. If implementation hardcoded `"tasks"` / `"archive"` instead of reading `config.paths.tasks_dir` / `config.paths.archive_dir`, tests would still pass.

**Fix (from reviewer + precedent at `tests/test_config_schema_1171.py:314-328`):**

- Use non-default sentinel values (e.g., `tasks_dir="sentinel_tasks"`, `archive_dir="sentinel_archive"`) in the `_PathsConfig` fixture
- Runtime tests must assert resolved paths contain the sentinel — this proves the function reads from `config.paths.*` rather than using hardcoded defaults
- Per-function positive assertions: each tested function (`scan_and_fix`, `detect_corruption`, `_is_archive_path`, `write_task`, `write_task_if_unchanged`, `list_task_files`, `list_archive_files`, `move_to_archive`) must demonstrate it uses the configured path value

### Refined AC Text (replaces AC1/AC2)

- AC1: Tests validate corruption.py uses sub-model access paths — config fixture must use non-default sentinel values (`tasks_dir != "tasks"`, `archive_dir != "archive"`) and runtime assertions must prove each function resolves paths via `config.paths.*` (not hardcoded defaults)
- AC2: Tests validate storage.py non-save_config sites use sub-model access paths — config fixture must use non-default sentinel values and per-function runtime assertions must prove `write_task`, `write_task_if_unchanged`, `list_task_files`, `list_archive_files`, `move_to_archive` resolve paths via `config.paths.*`

### Architecture Notes

- Precedent: `tests/test_config_schema_1171.py:314-328` uses `"custom-tasks"` / `"custom-archive"` for extraction proof
- No new interfaces, dependencies, or security surface
- Task is `type:test` — test-writer pass-through, builder adjusts existing test

### Loop-Breaker Resolution

Three prior review failures traced to: (1) AC4 ambiguity (fixed in cycle 1), (2-3) AC1/AC2 default-value false-green. Refined AC now provides unambiguous sentinel-value proof requirement. Adjacent precedent confirms pattern works.

### Challenge Results

- Challenger: SKIPPED — refinement-only cycle on previously-challenged test task; no new architectural surface
- Rationale: Original approval challenger ran in cycle 1; this cycle only tightens proof requirements

### Test Depth

- Max depth: 1
- Test-writer: PROCEED

### Verdict: APPROVE

### Action Taken: Refined AC1/AC2 to require non-default sentinel path values in test fixtures, preventing false-green from hardcoded defaults. Advancing to todo

[[2026-04-29]]
REFINE → approve. AC1/AC2 refined to require non-default sentinel path values in test fixtures (e.g. tasks_dir="sentinel_tasks", archive_dir="sentinel_archive") so hardcoded default literals cannot false-green. Per-function positive assertions required. Precedent: tests/test_config_schema_1171.py:314-328. All td:1. Advancing to todo.

[[2026-04-30]]

## Test-Writer Notes

- Retry: added 8 new sentinel-value tests for AC1/AC2 reviewer gaps.
- Test file: `tests/test_support_migration_1175.py`
- New tests added:
  - `TestFromAC_CorruptionSubModelPaths`: `test_scan_and_fix_reads_sentinel_tasks_dir`, `test_scan_and_fix_reads_sentinel_archive_dir`, `test_is_archive_path_uses_sentinel_archive_dir` (3 tests)
  - `TestFromAC_StorageNonSaveConfigPaths`: `test_write_task_writes_to_sentinel_tasks_dir`, `test_write_task_if_unchanged_reads_sentinel_tasks_dir`, `test_list_task_files_reads_sentinel_tasks_dir`, `test_list_archive_files_reads_sentinel_archive_dir`, `test_move_to_archive_uses_sentinel_dirs` (5 tests)
- Total: 48 tests, all PASS (40 existing + 8 new).
- Builder skip: test-only retry per Step 1b.1. All 8 new sentinel-value tests pass against current implementation — corruption.py and storage.py already use `config.paths.tasks_dir` / `config.paths.archive_dir` throughout. Sentinel proof (non-default `tasks_dir="sentinel_tasks"`, `archive_dir="sentinel_archive"`) confirms hardcoded defaults cannot false-green.
- Lint: ruff exit 0 (clean).
- AC1/AC2 proof-strength gap resolved: sentinel dirs created exclusively (no 'tasks'/'archive' dirs), so hardcoded defaults would cause FileNotFoundError or empty results — tests cannot pass unless functions read from `config.paths.*`.
[[2026-04-30]]

## Builder Notes

- Implementation: no source or test file changes (test-only retry with builder skip conditions already satisfied).
- Verification: quality-runner scoped run on `tests/test_support_migration_1175.py` confirms 48 passed, 0 failed, 0 skipped.
- Lint: ruff clean on `tests/test_support_migration_1175.py`.
- Coverage: not gate-blocking for this builder pass-through; no module touched in GREEN phase.
- Evidence summary: task remains test-only; current implementation already satisfies sentinel-path proof assertions added by test-writer.
- Fixes applied: none (no code defects requiring builder intervention).
[[2026-04-30]]

## Review Evidence

### Changed Scope

- Reviewed the task-owned retry in tests/test_support_migration_1175.py.
- Verified supporting implementation and live config at serve/kanban/src/owlbear_kanban/corruption.py, serve/kanban/src/owlbear_kanban/storage.py, serve/kanban/src/owlbear_kanban/models.py, serve/kanban/src/owlbear_kanban/config_loader.py, and .owlbear/kanban/config.yml.

### Test Results

- pytest: 48 passed, 0 failed, 0 skipped (quality-runner scoped to tests/test_support_migration_1175.py)

### Lint

- ruff: clean (quality-runner scoped to tests/test_support_migration_1175.py)

### Coverage

- N/A for gate: td:1 test-only retry with no source diff in this cycle.
- Informational only: the scoped run reported low package-wide coverage because one task-owned test file was measured against the full package surface.

### Pass 1 - CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: corruption.py uses sub-model access paths for all 8 identified access sites | TestFromAC_CorruptionSubModelPaths | Yes. Sentinel-only runtime proofs at tests/test_support_migration_1175.py:282-376 create sentinel_tasks and sentinel_archive exclusively, so hardcoded tasks or archive paths would return no findings or misclassify archive files. Current source reads config.paths.tasks_dir and config.paths.archive_dir at corruption.py:586-587 and 675. | COVERED |
| AC2: storage.py non-save_config sites use sub-model access paths for all 9 identified sites | TestFromAC_StorageNonSaveConfigPaths | Yes. Sentinel-only runtime proofs at tests/test_support_migration_1175.py:517-665 force write_task, write_task_if_unchanged, list_task_files, list_archive_files, and move_to_archive to resolve configured directories. write_task_if_unchanged also acquires the archive lock path before lookup at storage.py:479-484, and engine.py:401-419 opens that concrete path, so hardcoded archive would fail. Current non-save_config source sites are storage.py:415,479-480,507,523,546-547. | COVERED |
| AC3: BoardConfig no longer exposes forwarding properties | TestFromAC_CompatLayerRemoval | Yes. Direct BoardConfig.**dict** checks at tests/test_support_migration_1175.py:682-778 fail if any forwarding property remains. Current BoardConfig keeps only status_names as a property at models.py:395-398. | COVERED |
| AC4: live config.yml loads via canonical load_config() with value-equality proof | TestFromAC_LiveConfigGroupedFormat | Yes. The test exercises config_loader.load_config and asserts config.pipeline.statuses == config.statuses plus len == 7 at tests/test_support_migration_1175.py:853-872. That matches the canonical loader entry at config_loader.py:25-35 and the grouped normalizer behavior in models.py:214-318. | COVERED |
| AC5: terminal_status present in live config | TestFromAC_LiveConfigTerminalStatus | Yes. Raw-YAML assertions at tests/test_support_migration_1175.py:892-924 fail if pipeline.terminal_status is absent or mismatched. The live config defines terminal_status under pipeline in .owlbear/kanban/config.yml:16-21. | COVERED |

#### Security Review

- No issues. This retry is test-only and adds no runtime input surface, persistence path, dependency, or secret handling.

#### Test Integrity

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| Existing TestFromAC classes in tests/test_support_migration_1175.py | Retry added 8 sentinel-path proofs and strengthened the prior AC1 and AC2 false-green cases. No builder-authored weakening or removal detected. Scoped pytest reported 0 skipped, so the live-config skipif guards did not hide failures in this workspace. | STRENGTHENED |

#### Test Quality

| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Sentinel directories and exact path-parent assertions at tests/test_support_migration_1175.py:282-376 and 517-665 fail on hardcoded defaults. |
| Negative or error-path coverage | ADEQUATE | Task scope is migration-proof coverage rather than broad failure semantics; the suite still exercises false-green failure modes directly. |
| Manual mutation reasoning | STRONG | Replacing config.paths.* with hardcoded tasks or archive in the covered functions would fail the sentinel tests. |
| Test independence | STRONG | Each test builds its own temp board and patched config; no shared mutable state. |
| Descriptive names | STRONG | Test names map directly to the function and migration proof being asserted. |

#### Data Safety

- No issues.

#### Implementation-Aware Gaps

- No significant untested path remains within AC scope. The prior AC1 and AC2 proof gap is closed by the sentinel-only runtime checks, including the write_task_if_unchanged archive-lock path proof.

#### Builder Process Quality

| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Approach variation | Yes |
| Assessment | CLEAN |

### Pass 2 - INFORMATIONAL

- Some source-level assertions remain string-based, but the sentinel runtime checks now provide the binding behavioral proof that was missing in prior review cycles.

### AC Compliance

| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | tests/test_support_migration_1175.py:282-376 and corruption.py:586-587,675 | TestFromAC_CorruptionSubModelPaths | PASS |
| AC2 | tests/test_support_migration_1175.py:517-665, storage.py:415,479-480,507,523,546-547, and engine.py:401-419 | TestFromAC_StorageNonSaveConfigPaths | PASS |
| AC3 | tests/test_support_migration_1175.py:682-778 and models.py:395-398 | TestFromAC_CompatLayerRemoval | PASS |
| AC4 | tests/test_support_migration_1175.py:853-872, config_loader.py:25-35, and models.py:214-318 | TestFromAC_LiveConfigGroupedFormat | PASS |
| AC5 | tests/test_support_migration_1175.py:892-924 and .owlbear/kanban/config.yml:16-21 | TestFromAC_LiveConfigTerminalStatus | PASS |

### Deductions

- None.

### Confidence: 0.95

### Verdict: PASS

### Action: advance to docs

### Post-task Reflection

- The prior false-green on default path names is fully addressed only once sentinel directories are exclusive, not merely different in config.
- write_task_if_unchanged proof depends on the archive lock path being exercised before lookup, so engine.py lock semantics matter to the review evidence.
- Low package-wide coverage on a single scoped test file is noise for td:1 test-only retries and should stay informational, not gate-blocking.
[[2026-04-30]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Test-only task; no source behavior, API, CLI, or config changes |
| 2 | Module docstrings | No | N/A | No Python source modules modified (builder skip; no source diff) |
| 3 | External attribution | No | N/A | No external patterns referenced in task body |
| 4 | Research doc | No | N/A | No `.owlbear/research/` file produced |
| 5 | Diagram maintenance (describes match) | No | N/A | `kanban.excalidraw` describes `serve/kanban/src/**` — no files in that glob changed in this task |
| 6 | Explicit diagram creation | No | N/A | Not requested |
| 7 | Deletion detection | No | N/A | No deleted files |

### Scope Classification

| File | Scope | Action |
|------|-------|--------|
| tests/test_support_migration_1175.py | OUT | N/A (test file) |

### Files Updated

- None

### Child Tasks Created

- None

### Scratch Files Cleaned

- None (no `.owlbear/scratch/1175-*` files found)
[[2026-04-30]]

## Audit

### AC Verification

| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: corruption.py sub-model paths (sentinel) | tests/test_support_migration_1175.py:282-376 — sentinel-only dirs, hardcoded defaults would fail | PASS |
| AC2: storage.py non-save_config paths (sentinel) | tests/test_support_migration_1175.py:517-665 — per-function sentinel proofs for write_task, list_task_files, list_archive_files, move_to_archive | PASS |
| AC3: BoardConfig no forwarding properties | tests/test_support_migration_1175.py:682-778 — **dict** property assertions | PASS |
| AC4: live config via load_config with value-equality | tests/test_support_migration_1175.py:853-872 — config.pipeline.statuses == config.statuses, len == 7 | PASS |
| AC5: terminal_status in live config | tests/test_support_migration_1175.py:892-924 — raw YAML assertions | PASS |

### Test Results

- pytest (full): 3209 passed, 28 failed, 4 skipped
- Task-scoped (tests/test_support_migration_1175.py): 48 passed, 0 failed
- Failed tests are pre-existing from sibling tasks (1171, 1068 forwarding property tests broken by earlier compat removal phases) and module-level tests (test-curator scope)
- tests/test_storage_1175.py (8 failures): orphaned RED tests from superseded task definition (save_config hardening); current scope explicitly excludes save_config

### Lint

- ruff: clean in task scope (4 violations in unrelated packages: knowledge, mcp-memory, orchestrator)

### Process Concerns

1. **Uncommitted deliverable:** tests/test_support_migration_1175.py has 260 uncommitted insertions (sentinel tests from final cycle). Upstream agents did not commit before advancing. Per audit protocol: noted, not silently committed.
2. **Orphaned test file:** tests/test_storage_1175.py (8 failing tests) is from a prior task definition when #1175 was titled "Harden storage save_config." Task was re-scoped but old test file was never removed.

### Architect Quality: 3/5

Two refinement cycles required: AC4 ambiguity caused 2 review failures, then AC1/AC2 default-value false-green caused another. Final refined AC is precise and verifiable, but initial quality caused significant pipeline churn.

### Deduction Breakdown

- AC quality score 3: -0.03
- No AC lines without evidence
- No lint in task scope
- No task-scope test failures (current AC tests all pass; orphaned file is from superseded scope)
- Reviewer evidence section present and detailed

### Confidence: 0.97

### Action: archive

### Upstream Commits

- c0a2d625 test: add canonical loader proof for AC4 live config (#1175, test-writer) — committed
- 7f2264b2 test: add failing tests for support module migration and compat removal (#1175, test-writer) — committed
- NOTE: Final sentinel-value cycle (260 lines) is UNCOMMITTED in working tree

### Follow-up needed

- Commit the uncommitted sentinel tests in tests/test_support_migration_1175.py
- Remove or re-scope orphaned tests/test_storage_1175.py (dead AC, always-failing)
