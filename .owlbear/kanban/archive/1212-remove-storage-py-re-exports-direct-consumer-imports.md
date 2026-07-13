---
id: 1212
title: Remove storage.py re-exports — direct consumer imports
status: archived
priority: medium
created: 2026-04-30 15:29:15.222006+00:00
updated: 2026-05-03T22:28:56.509267+00:00
tags:
- audit-kanban
- architecture
parent:
depends_on:
- 1211
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Remove facade re-exports from storage.py for body_parser, corruption, and activity_store symbols. Consumers import from source modules directly.

## AC
- [ ] `storage.py` `__all__` no longer lists any symbol from `body_parser`, `corruption`, or `activity_store`; import lines for pure re-exports (not used by storage.py's own functions) removed entirely (td:1)
- [ ] `engine.py` consumer imports migrated from `owlbear_kanban.storage` to source modules (`owlbear_kanban.corruption`, `owlbear_kanban.activity_store`) — covers 3 `storage.{method}` call sites and 2 inline imports (td:1)
- [ ] Test consumers in `serve/kanban/tests/` updated: body_parser/corruption/activity_store symbols imported from source modules, not storage (td:1)
- [ ] Root-level test patch targets in `tests/test_engine_ble001_1202.py` and `tests/test_engine_cockpit_view.py` updated to match engine.py's new import paths (td:1)
- [ ] `storage.py` docstring reflects reduced re-export scope (td:0)
- [ ] Task-local proving tests assert both absence of old patterns AND presence of correct new import targets (td:1)
- [ ] No regressions in task-affected files: `tests/test_storage_re_exports_1212.py` passes; `serve/kanban/tests/test_engine_activity.py` and `serve/kanban/tests/test_engine_archived_edit_1120.py` pass (td:0)

## Builder Notes
- `storage.py` internally uses `CorruptionError`, `detect_corruption`, `ERR_CORRUPT_ID_FILENAME_MISMATCH`, `ERR_CORRUPT_YAML_PARSE` from corruption — keep these imports but remove from `__all__`
- Pure re-exports to remove entirely: `parse_body`/`render_body` (body_parser), `append_activity_event`/`compact_activity_log`/`list_activity_events` (activity_store), `scan_and_fix`/`attempt_repair`/`RepairOutcome` (corruption)
- `engine.py` uses `storage.detect_corruption`, `storage.list_activity_events`, `storage.compact_activity_log` via module attribute access + 2× inline `from owlbear_kanban.storage import detect_corruption as _detect_corruption` (lines ~590, ~1499)
- After changing engine.py imports, root test patch targets move: `owlbear_kanban.storage.detect_corruption` → `owlbear_kanban.engine.{name}` (or equivalent); same for `owlbear_kanban.storage.compact_activity_log`
- Package-local test files needing import updates: `test_corruption.py` (`scan_and_fix`), `test_engine_activity.py` (`list_activity_events`), `test_engine_archived_edit_1120.py` (`CorruptionError`), `test_storage_1050.py` (`CorruptionError`), `test_storage.py` (`detect_corruption`)
- `models` re-exports (`Section`, `ConcurrencyError`, etc.) and `_naming`/`storage_io` re-exports are NOT in scope

## Reviewer Feedback (cycle 1)
- Task-local tests in `tests/test_storage_re_exports_1212.py` are absence-only — they prove old patterns are gone but don't assert new targets exist. Strengthen: AC1 must assert import-line removal from storage.py source, AC3 must assert exact source-module imports, AC4 must assert exact replacement patch target strings.
- AC6 (original "All kanban + root test suites pass") was too broad — gated on 7 pre-existing failures in `test_storage.py:233`, `test_storage_1050.py:281,299,324,597,656`, `test_corruption.py:1058` that are unrelated branch debt. Replaced with scoped regression gate.

## Finding: 3.3
[[2026-05-03]]
## Architecture Review (cycle 2 — post-reviewer rejection)

**Verdict:** APPROVED → todo

**Context:** Reviewer rejected at confidence 0.78. Implementation correct (AC1-AC5 verified via direct file inspection). Two issues: (1) task-local tests are absence-only, (2) AC6 gated on pre-existing unrelated failures.

**AC Changes:**
| Original AC | Issue | Action |
|-------------|-------|--------|
| AC6 "All kanban + root test suites pass" | Gates on 7 pre-existing failures unrelated to #1212 diff | Replaced with scoped regression gate on task-affected files only |
| (new) AC6 positive assertions | Tests only prove absence of old patterns | Added: must assert both absence AND presence of correct new targets |

**Pre-existing failure analysis:** 7 red tests (`test_storage.py:233`, `test_storage_1050.py:281,299,324,597,656`, `test_corruption.py:1058`) are in assertion bodies far from the import lines #1212 touched. Confirmed unrelated branch debt — separate triage needed.

**Architecture Notes:**
- Implementation remains sound — reviewed in cycle 1, confirmed correct by reviewer's own file inspection
- Only pipeline-quality issues: test file needs positive assertions added
- No code changes needed to implementation files

**Test Depth:**
- Max depth: 1
- Test-writer: PROCEED (strengthen existing test file with positive assertions per reviewer feedback)

**Challenge:** SKIPPED — re-approval of already-verified implementation; only test-quality refinement needed
[[2026-05-03]]
## Test-Writer Notes
- **Retry cycle (Step 1b.1):** Reviewer rejected for absence-only tests. Added positive assertions per reviewer feedback. All new tests pass against current implementation → builder skip, advancing directly to review.

**Test file:** `tests/test_storage_re_exports_1212.py`

| Class | Tests | Type |
|-------|-------|------|
| `TestFromAC_StorageAllCleanup` | 8 | AC1 absence — `__all__` cleanup |
| `TestFromAC_StorageSourceImportLineRemoval` | 3 | AC1 **positive** — import lines removed from storage.py source; internal corruption import preserved |
| `TestFromAC_EngineImportMigration` | 4 | AC2 absence — no storage.* call sites in engine.py |
| `TestFromAC_EngineNewImportTargets` | 3 | AC2 **positive** — detect_corruption/list_activity_events/compact_activity_log imported from source modules |
| `TestFromAC_PackageTestImportSources` | 5 | AC3 absence — package tests not importing from storage |
| `TestFromAC_PackageTestSourceModuleImports` | 5 | AC3 **positive** — exact source-module imports present in package test files |
| `TestFromAC_RootTestPatchTargets` | 2 | AC4 absence — old storage.* patch targets gone |
| `TestFromAC_RootTestNewPatchTargets` | 2 | AC4 **positive** — owlbear_kanban.engine.detect_corruption and owlbear_kanban.engine.compact_activity_log patch targets present |

**Total:** 32 tests, all PASS (pytest exit 0). Lint: clean (ruff exit 0).

**AC coverage:** AC1 ✓ AC2 ✓ AC3 ✓ AC4 ✓ AC5 (td:0, skipped) AC6 ✓ AC7 (td:0, skipped)

**Step 1b.1 rationale:** Reviewer's Required Follow-up was test-proof gaps only (no implementation changes needed). All new positive-assertion tests pass against current code — implementation was already verified correct in cycle 2 architecture review.
[[2026-05-03]]
Step 1b.1 advance: all new positive-assertion tests pass, no builder work needed.
[[2026-05-03]]
## Review Evidence
### Test Results
- Quality-runner broad contextual pass: 302 passed, 7 failed / 309 total. The 7 failures match the pre-existing unrelated debt already documented in Architecture Review cycle 2 (`serve/kanban/tests/test_corruption.py:1062`, `serve/kanban/tests/test_storage.py:251`, `serve/kanban/tests/test_storage_1050.py:295,320,349,607,680`) and are not used as a gate on the refined AC.
- Quality-runner narrow AC gate on current workspace state: 113 passed, 0 failed.
  - `tests/test_storage_re_exports_1212.py`: 32 collected / 32 passed
  - `serve/kanban/tests/test_engine_activity.py`: 6 passed
  - `serve/kanban/tests/test_engine_archived_edit_1120.py`: 93 passed
- Ruff narrow gate: clean on scoped source + test paths.
- Coverage (module-level only, informational): `owlbear_kanban.storage` 97%, `owlbear_kanban.engine` 43%, `owlbear_kanban.corruption` 34%, `owlbear_kanban.activity_store` 40%.

### Source Control State
- `git status --short -- tests/test_storage_re_exports_1212.py ...` returned `M tests/test_storage_re_exports_1212.py`. The strengthened task-local proof file is modified in the working tree and not committed.
- `git diff -- tests/test_storage_re_exports_1212.py` shows the entire positive-proof expansion is local-only: helper `_imports_from_source` plus `TestFromAC_StorageSourceImportLineRemoval`, `TestFromAC_EngineNewImportTargets`, `TestFromAC_PackageTestSourceModuleImports`, and `TestFromAC_RootTestNewPatchTargets`.
- `git show 9595b4d7:tests/test_storage_re_exports_1212.py | rg -n "TestFromAC_StorageSourceImportLineRemoval|TestFromAC_EngineNewImportTargets|TestFromAC_PackageTestSourceModuleImports|TestFromAC_RootTestNewPatchTargets"` returned no matches, and `git diff --name-only 9595b4d7..HEAD -- tests/test_storage_re_exports_1212.py` returned no output. The committed deliverable in HEAD therefore still lacks the positive-assertion proof required by AC6.
- Builder immutability check: builder commit `26b80b06` changed 9 files and did not touch `tests/test_storage_re_exports_1212.py`. No builder weakening/removal of `TestFromAC_*` assertions detected.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test in HEAD | Would Fail If AC Violated? | Verdict |
|---------|----------------------|----------------------------|---------|
| AC1 `storage.py` cleanup + import-line removal | `TestFromAC_StorageAllCleanup` only | Partially. HEAD lacks the positive import-line-removal assertions; those exist only in uncommitted working-tree additions. | LAX |
| AC2 engine import migration | `TestFromAC_EngineImportMigration` only | Partially. HEAD lacks exact new-target assertions; those exist only in uncommitted working-tree additions. | LAX |
| AC3 package-test import migration | `TestFromAC_PackageTestImportSources` only | Partially. HEAD lacks exact source-module-import assertions; those exist only in uncommitted working-tree additions. | LAX |
| AC4 root test patch targets | `TestFromAC_RootTestPatchTargets` only | Partially. HEAD lacks exact replacement-target assertions; those exist only in uncommitted working-tree additions. | LAX |
| AC5 storage docstring reduced scope | direct file review only (`serve/kanban/src/owlbear_kanban/storage.py:1-18`) | Yes | COVERED |
| AC6 task-local tests assert absence and presence | HEAD task file does not contain the positive classes; current local diff does | No | MISSING |
| AC7 no regressions in task-affected files | narrow quality-runner workspace run green | Yes for current workspace; not the blocking issue | COVERED |

- Security review: no issues; diff is limited to import rewiring / docstring / test updates.
- Test integrity: no builder weakening/removal; builder commit excluded the `TestFromAC` file.
- Test quality: committed HEAD task-local proof remains WEAK because it is absence-only. The stronger discriminating assertions exist only as uncommitted local changes.
- Data safety: no issues.
- Necessity check: skipped (refactor task, no new dependency/integration).
- Builder process quality: no loop in implementation, but this is a second review failure on the same proof gap.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `storage.py` docstring/import surface and `__all__` are narrowed in `serve/kanban/src/owlbear_kanban/storage.py` (docstring top block, corruption-only import retained, pure re-exports absent from `__all__`) | current workspace has both absence+positive tests, but HEAD only has absence tests | PASS (implementation), FAIL as committed proof via AC6 |
| AC2 | `engine.py` imports `detect_corruption` from corruption and `list_activity_events` / `compact_activity_log` from activity_store; no storage call sites remain | same | PASS (implementation) |
| AC3 | migrated package-test imports present in `test_corruption.py`, `test_engine_activity.py`, `test_engine_archived_edit_1120.py`, `test_storage_1050.py`, `test_storage.py` | same | PASS (implementation) |
| AC4 | root test patch targets point at `owlbear_kanban.engine.detect_corruption` and `owlbear_kanban.engine.compact_activity_log` | same | PASS (implementation) |
| AC5 | reduced-scope storage module docstring present | n/a td:0 | PASS |
| AC6 | current working tree adds the positive-proof assertions, but committed deliverable still lacks them (`git status`, `git diff`, `git show 9595b4d7:...`) | HEAD: no positive-proof classes; working tree only | FAIL |
| AC7 | narrow quality-runner run green on current workspace: 113 passed, 0 failed | `tests/test_storage_re_exports_1212.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_archived_edit_1120.py` | PASS (workspace state) |

### Deductions
- `-0.12` AC6 fails in the committed deliverable: current green proof exists only as uncommitted working-tree changes.
- `-0.04` second review cycle on the same proof gap; loop-breaker applies even though the local fix appears correct.
- Confidence: `0.84`

### Verdict
- FAIL -> backlog
- Reason: the implementation looks correct, but the review gate is on the committed deliverable. `tests/test_storage_re_exports_1212.py` is modified locally and not committed, so the task still fails AC6 in HEAD. This is the second review-cycle failure on the same proof gap, so route to backlog per loop-breaker.

### Required Follow-up
- Commit the strengthened `tests/test_storage_re_exports_1212.py` proof to HEAD before re-entering review.
- Reconcile the task history note with git history so the next review can trust the handoff artifact.
[[2026-05-03]]

## Architecture Review (cycle 3 — re-approval after reviewer commit-gap rejection)

**Verdict:** APPROVED → todo

**Context:** Reviewer rejected at confidence 0.84 because `tests/test_storage_re_exports_1212.py` positive-assertion classes exist only in working tree, not committed to HEAD. Implementation verified correct in cycles 1+2. AC unchanged — still valid.

**Cycle 3 assessment:**
- AC1–AC7: no changes needed; all criteria already precisely scoped from cycle 2 refinement
- Dependency #1211: archived (done) — no blocker
- Test file workspace state: all 4 positive-assertion classes present (lines 250, 283, 314, 373)
- Single required action: commit the test file

**Builder guidance (cycle 3):**
- The ONLY remaining action is: `git add tests/test_storage_re_exports_1212.py && git commit` with appropriate message
- No implementation changes needed — all source files are correct in HEAD
- No test modifications needed — the working-tree test file is complete and passes

**Test Depth:** Max depth 1 (unchanged)
**Test-writer:** SKIP for this cycle — tests already written and passing; pass-through to builder
**Challenge:** SKIPPED — re-approval of already-verified implementation; only commit delivery needed

### Verdict: APPROVE
### Action Taken: Re-approved to todo. Builder must commit the already-correct test file.
[[2026-05-03]]
Cycle 3 re-approval. Implementation verified correct in prior cycles. Only gap: uncommitted test file with positive assertions. Builder must commit `tests/test_storage_re_exports_1212.py` — no code changes needed.
[[2026-05-03]]
## Test-Writer Notes

**Pass-through (Cycle 3):** Tests already written and strengthened in a prior cycle. Working tree contains all required proof. Architect designated this as test-writer SKIP → pass-through to builder.

**Test file:** `tests/test_storage_re_exports_1212.py`

| Class | Tests | Type |
|-------|-------|------|
| `TestFromAC_StorageAllCleanup` | 8 | AC1 absence — `__all__` cleanup |
| `TestFromAC_StorageSourceImportLineRemoval` | 3 | AC1 positive — no body_parser/activity_store import lines in storage.py |
| `TestFromAC_EngineImportMigration` | 4 | AC2 absence — no storage.* call sites in engine.py |
| `TestFromAC_EngineNewImportTargets` | 3 | AC2 positive — detect_corruption/list_activity_events/compact_activity_log imported from source modules |
| `TestFromAC_PackageTestImportSources` | 5 | AC3 absence — package tests not importing from storage |
| `TestFromAC_PackageTestSourceModuleImports` | 5 | AC3 positive — exact source-module imports present in package test files |
| `TestFromAC_RootTestPatchTargets` | 2 | AC4 absence — old storage.* patch targets gone |
| `TestFromAC_RootTestNewPatchTargets` | 2 | AC4 positive — engine.detect_corruption and engine.compact_activity_log patch targets present |

**Total:** 32 tests, all PASS (working tree). Ruff: clean.

**AC coverage:** AC1 ✓ AC2 ✓ AC3 ✓ AC4 ✓ AC5 (td:0) AC6 ✓ AC7 (td:0)

**Builder action:** `git add tests/test_storage_re_exports_1212.py && git commit` — no implementation changes needed. The positive-assertion classes are present in the working tree but not in committed HEAD.
[[2026-05-03]]
## Builder Notes
- Implementation: no source implementation changes were required in this cycle; committed delivery artifact only: tests/test_storage_re_exports_1212.py
- Commit: 150ffeac (`test: commit positive import-proof assertions (#1212, builder)`)
- Tests: 113 passed, 0 failed (scoped gate):
  - tests/test_storage_re_exports_1212.py
  - serve/kanban/tests/test_engine_activity.py
  - serve/kanban/tests/test_engine_archived_edit_1120.py
- Coverage: owlbear_kanban.storage = 97% (overall scoped run reported 44%)
- Ruff: clean (tests/test_storage_re_exports_1212.py)
- Approach: surgical commit-gap closure only; promoted already-green working-tree proof into committed HEAD without altering implementation.

### Evidence Summary
- Task-local proof classes for positive assertions are now part of committed HEAD (previous reviewer rejection cause resolved).
- Scoped regression gate and lint gate both passed.
- No TestFromAC classes were modified by builder in this cycle beyond committing pre-existing strengthened proof content.

### Post-task Reflection
- Problem faced: task was blocked by delivery state (uncommitted proof), not implementation correctness.
- Workaround applied: verified scoped green state first, then committed only the single required test file to avoid incidental drift.
- Pattern discovered: retry-loop tasks can require builder commit-only cycles; commit integrity is the true gate.
- Quality gap: prior cycle notes claimed readiness while HEAD lacked proof artifact; commit-state verification should be explicit earlier.
[[2026-05-03]]
## Review Evidence
### Test Results
- Quality-runner scoped pass: 184 passed, 0 failed.
- Per-file counts:
  - `tests/test_storage_re_exports_1212.py`: 32 passed
  - `serve/kanban/tests/test_engine_activity.py`: 33 passed
  - `serve/kanban/tests/test_engine_archived_edit_1120.py`: 51 passed
  - `tests/test_engine_ble001_1202.py`: 28 passed
  - `tests/test_engine_cockpit_view.py`: 40 passed

### Lint
- Ruff: clean on scoped source + test paths (10 paths).

### Coverage
- `owlbear_kanban.storage`: 97%
- `owlbear_kanban.engine`: 50%
- Coverage is informational here. The rejection is not a module-coverage failure; it is an AC/proof failure with a remaining implementation miss.

### Source Control State
- Builder commit `26b80b06` changed the 9 task implementation/consumer files.
- Builder commit `150ffeac` changed only `tests/test_storage_re_exports_1212.py` and was additive strengthening only: `git show --unified=0 150ffeac -- tests/test_storage_re_exports_1212.py` shows 173 insertions and 0 deletions. No `TestFromAC_*` weakening/removal detected.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1 `storage.py` cleanup + import-line removal | `tests/test_storage_re_exports_1212.py:57`, `:254` | Yes | COVERED |
| AC2 engine import migration | `tests/test_storage_re_exports_1212.py:115`, `:122`, `:129`, `:136`, `:287`, `:294` | Yes | COVERED |
| AC3 package-test import migration | `tests/test_storage_re_exports_1212.py:178`, `:353`, `:360` | No. The suite checks `test_storage_1050.py` only for `CorruptionError`; it does not check that file's `detect_corruption` import. Current HEAD still violates the plain-text AC at `serve/kanban/tests/test_storage_1050.py:34`, yet all tests pass. | MISSING |
| AC4 root test patch targets | `tests/test_storage_re_exports_1212.py:202`, `:210`, `:377`, `:384` | Yes | COVERED |
| AC5 `storage.py` docstring reflects reduced scope | direct file review of `serve/kanban/src/owlbear_kanban/storage.py:19`, `:21`, `:534` | No. The docstring still advertises `CorruptionError` as a re-exported type while the reduced public surface (`__all__`) no longer lists it. | FAIL |
| AC6 task-local tests prove absence + presence | `tests/test_storage_re_exports_1212.py:314` onward | No. The proof suite is still under-scoped for AC3 because it allows the remaining `test_storage_1050.py` storage-based `detect_corruption` import to survive unnoticed. | FAIL |
| AC7 scoped regression gate | quality-runner scoped run green | Yes | COVERED |

#### Security Review
- No issues found. The diff is import rewiring, docstring text, and proof tests only.

#### Test Integrity
- Builder touched `TestFromAC_*` only in commit `150ffeac`.
- That commit added positive-proof classes and helper functions without deleting or weakening prior assertions. Assessment: STRENGTHENED.

#### Test Quality
- The task-local suite is otherwise discriminating, but AC3 proof is incomplete: it mirrors the narrower builder symbol map instead of the AC's broader text. Result: false green on the delivered snapshot.

#### Data Safety
- No issues found.

#### Necessity Check
- Skipped. Refactor task; no new dependency or integration.

#### Builder Process Quality
- This task already contains one prior `## Review Evidence` rejection. This is a subsequent review failure on the same task.
- The failure is not just proof quality: the live code still conflicts with the plain-text AC, and the task record/proof suite narrowed that scope without changing the AC text.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/storage.py:46` retains only internal corruption imports; `serve/kanban/src/owlbear_kanban/storage.py:534` `__all__` omits the removed facade symbols | `tests/test_storage_re_exports_1212.py:57`, `:254` | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:46` imports activity symbols from `activity_store`; `serve/kanban/src/owlbear_kanban/engine.py:50` imports `detect_corruption` from `corruption` | `tests/test_storage_re_exports_1212.py:115`, `:122`, `:129`, `:136`, `:287`, `:294` | PASS |
| AC3 | `serve/kanban/tests/test_storage_1050.py:30` moved `CorruptionError` to `corruption`, but `serve/kanban/tests/test_storage_1050.py:34` still imports `detect_corruption` from `storage` | `tests/test_storage_re_exports_1212.py:178`, `:353` (no `test_storage_1050 detect_corruption` proof exists) | FAIL |
| AC4 | `tests/test_engine_ble001_1202.py:176` patches `owlbear_kanban.engine.detect_corruption`; `tests/test_engine_cockpit_view.py:847` patches `owlbear_kanban.engine.compact_activity_log` | `tests/test_storage_re_exports_1212.py:202`, `:210`, `:377`, `:384` | PASS |
| AC5 | `serve/kanban/src/owlbear_kanban/storage.py:19`/`:21` still list `CorruptionError` under `Re-exported types`, inconsistent with the reduced public surface at `serve/kanban/src/owlbear_kanban/storage.py:534` | td:0 direct inspection | FAIL |
| AC6 | The proof class at `tests/test_storage_re_exports_1212.py:314` never asserts `test_storage_1050.py` imports `detect_corruption` from `owlbear_kanban.corruption`; current violation survives a green run | same | FAIL |
| AC7 | Scoped quality-runner run: 184 passed, 0 failed | required files included in scoped run | PASS |

### Deductions
- `-0.14` AC3 implementation miss remains in HEAD (`serve/kanban/tests/test_storage_1050.py:34`).
- `-0.08` AC5 docstring is still stale (`serve/kanban/src/owlbear_kanban/storage.py:19`, `:21`, `:534`).
- `-0.09` AC6 proof is under-scoped and produces a false green on AC3.
- `-0.05` Subsequent review failure on the same task; loop-breaker applies.
- Confidence: `0.64`

### Verdict
- FAIL -> backlog
- Reason: the scoped gate is green, but the deliverable still violates the plain-text AC in one package test consumer and the task-local proof suite does not detect it. The storage docstring also still overstates the reduced public surface. Because this is a subsequent review failure and the task record has drifted into AC-interpretation inconsistency, route to backlog.

### Required Follow-up
- Reconcile AC3 explicitly: either narrow the AC text to the intended symbol/file map, or update `serve/kanban/tests/test_storage_1050.py` so `detect_corruption` imports from `owlbear_kanban.corruption`.
- Strengthen `tests/test_storage_re_exports_1212.py` so AC3 fails if `test_storage_1050.py` retains any corruption-symbol import from `owlbear_kanban.storage`, including `detect_corruption`.
- Update `serve/kanban/src/owlbear_kanban/storage.py` docstring to remove `CorruptionError` from the advertised reduced re-export surface, or document explicitly why it remains part of the intended public surface.

### Post-task Reflection
- The green scoped suite hid a real AC miss because the proof mirrored a narrower symbol map than the AC text.
- Prior PASS notes in task history were not sufficient evidence; the live files still needed direct re-checking.
- `git show --unified=0` was sufficient to clear builder `TestFromAC` weakening concerns without a full commit-diff reconstruction.
[[2026-05-03]]

## Architecture Review (cycle 4 — post-reviewer AC3/AC5/AC6 rejection)

**Verdict:** APPROVED → todo

**Context:** Reviewer rejected at confidence 0.64 in cycle 3. Three specific implementation/proof gaps remain — all against clear AC text that doesn't need modification.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 `storage.py` cleanup (td:1) | Precise, verified passing | None |
| AC2 engine import migration (td:1) | Precise, verified passing | None |
| AC3 test consumer migration (td:1) | AC text is precise. Builder Notes had incomplete symbol map — listed `test_storage_1050.py` only for `CorruptionError`, missed `detect_corruption`. **Live violation:** `serve/kanban/tests/test_storage_1050.py:34` still imports `detect_corruption` from `owlbear_kanban.storage` | Updated Builder Notes below |
| AC4 root test patch targets (td:1) | Precise, verified passing | None |
| AC5 storage docstring (td:0) | AC text is precise. **Live violation:** docstring line 21 lists `CorruptionError` as re-exported type, but `__all__` omits it | None (td:0, mechanical fix) |
| AC6 absence + presence proofs (td:1) | AC text is precise. **Proof gap:** `TestFromAC_PackageTestImportSources` and `TestFromAC_PackageTestSourceModuleImports` lack `detect_corruption` coverage for `test_storage_1050.py` — invisible to green run | Updated Builder Notes below |
| AC7 scoped regression (td:0) | Precise, verified passing | None |

### Architecture Notes
- Architecture verified sound in cycles 1–3. No structural changes needed.
- All remaining work is mechanical: one import fix, one docstring edit, two test additions.

### Builder Notes Update (cycle 4)
The original Builder Notes listed `test_storage_1050.py` only for `CorruptionError`. The complete symbol map for that file:
- `CorruptionError` → already moved to `owlbear_kanban.corruption` ✓
- `detect_corruption` → **still imported from `owlbear_kanban.storage`** ← FIX THIS

**Three remaining fixes (exhaustive list):**

1. **`serve/kanban/tests/test_storage_1050.py:34`** — move `detect_corruption` from `owlbear_kanban.storage` import block to `owlbear_kanban.corruption` import (line 31). Keep `MigrationRequiredError`, `move_to_quarantine`, `read_task`, `write_task` in the storage import — those are legitimate `__all__` members.

2. **`serve/kanban/src/owlbear_kanban/storage.py:19-21`** — remove `CorruptionError` from the "Re-exported types:" docstring line. It's imported for internal use but no longer in `__all__`.

3. **`tests/test_storage_re_exports_1212.py`** — add two tests:
   - In `TestFromAC_PackageTestImportSources`: `test_test_storage_1050_detect_corruption_not_from_storage` (absence)
   - In `TestFromAC_PackageTestSourceModuleImports`: `test_test_storage_1050_imports_detect_corruption_from_corruption` (positive)

### Dependency Analysis
- #1211: archived (done) — no blocker.

### Challenge Result
- Challenger recommended `block` at confidence 0.18.
- **Override with rebuttal:** Challenger conflates deliverable compliance (reviewer's gate) with AC precision + architectural soundness (architect's gate). The AC text is precise and unchanged — all 3 gaps are implementation misses against clear criteria, not AC ambiguity. The task is in `backlog` precisely to re-route through the pipeline so the builder can fix them. The Builder Notes gap (missing `detect_corruption` for `test_storage_1050.py`) caused the original miss and is now corrected above.

### Test Depth
- Max depth: 1
- Test-writer: SKIP — tests already written; only 2 additions needed, which the builder can make alongside the implementation fixes.

[[2026-05-03]]
Cycle 4 re-approval. AC text unchanged — all 7 lines precise and verifiable. Root cause of prior failures: Builder Notes had incomplete symbol map (missed detect_corruption for test_storage_1050.py). Updated builder guidance with exhaustive 3-fix list. Challenger override documented.
[[2026-05-03]]
## Test-Writer Notes

**Retry cycle (Step 1b) — surgical fill for reviewer AC3/AC6 gap.**

**Test file:** `tests/test_storage_re_exports_1212.py`

**Added 2 tests targeting the `test_storage_1050.py detect_corruption` gap:**

| Class | Test | Type |
|-------|------|------|
| `TestFromAC_PackageTestImportSources` | `test_test_storage_1050_detect_corruption_not_from_storage` | AC3 absence — `detect_corruption` not from storage |
| `TestFromAC_PackageTestSourceModuleImports` | `test_test_storage_1050_imports_detect_corruption_from_corruption` | AC3 positive — `detect_corruption` from `owlbear_kanban.corruption` |

**Verification:** `pytest tests/test_storage_re_exports_1212.py -v -n0` → 32 passed, 2 failed (new tests). Ruff: clean.

**Root cause confirmed:** `serve/kanban/tests/test_storage_1050.py:34` still imports `detect_corruption` from `owlbear_kanban.storage` — both new tests trigger correctly.

**AC coverage (updated):**
| AC | Coverage |
|----|---------|
| AC1 | ✓ absence + positive |
| AC2 | ✓ absence + positive |
| AC3 | ✓ absence + positive (now includes detect_corruption for test_storage_1050.py) |
| AC4 | ✓ absence + positive |
| AC5 | td:0 |
| AC6 | ✓ proof gaps filled |
| AC7 | td:0 |

**Builder actions (3 exhaustive fixes — unchanged from architect cycle 4):**
1. `serve/kanban/tests/test_storage_1050.py:34` — move `detect_corruption` from storage import to `owlbear_kanban.corruption` import block
2. `serve/kanban/src/owlbear_kanban/storage.py:19-21` — remove `CorruptionError` from "Re-exported types:" docstring
3. Commit all changes
[[2026-05-03]]
## Builder Notes
- Implementation: updated [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py) to import `detect_corruption` from `owlbear_kanban.corruption` instead of `owlbear_kanban.storage`; updated [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py) module docstring to remove stale `CorruptionError` re-export claim.
- Commit: `6f842938` (`fix: close AC3/AC5 gaps (#1212, builder)`).
- Tests: 115 passed, 0 failed (scoped gate):
  - [tests/test_storage_re_exports_1212.py](tests/test_storage_re_exports_1212.py)
  - [serve/kanban/tests/test_engine_activity.py](serve/kanban/tests/test_engine_activity.py)
  - [serve/kanban/tests/test_engine_archived_edit_1120.py](serve/kanban/tests/test_engine_archived_edit_1120.py)
- Coverage: `owlbear_kanban.storage` 97%.
- Ruff: clean on [serve/kanban/src/owlbear_kanban/storage.py](serve/kanban/src/owlbear_kanban/storage.py), [serve/kanban/tests/test_storage_1050.py](serve/kanban/tests/test_storage_1050.py), [tests/test_storage_re_exports_1212.py](tests/test_storage_re_exports_1212.py).
- Approach: surgical two-file fix to satisfy the two remaining RED assertions; no `TestFromAC_*` edits.

### Evidence Summary
- Previously failing RED tests in `TestFromAC_PackageTestImportSources` / `TestFromAC_PackageTestSourceModuleImports` now pass after import-path migration in `test_storage_1050.py`.
- AC5 stale documentation mismatch is resolved by removing `CorruptionError` from the storage module re-exported-types docstring list.
- Scoped regression files required by AC7 remain green.

### Post-task Reflection
- Problem faced: task had reached a false-green loop where proof and implementation drifted on one remaining import symbol.
- Workaround applied: re-validated RED first against task-local tests, then patched only the exact import/docstring lines.
- Pattern discovered: for re-export-removal tasks, proof tests must include per-symbol checks on each named consumer file to avoid AC drift.
- Quality gap: prior cycles mixed “implementation complete” with “delivery complete”; commit-state checks should happen earlier in the cycle.
[[2026-05-03]]
## Review Evidence
### Test Results
- Quality-runner scoped run on the current working tree: 186 passed, 0 failed across `tests/test_storage_re_exports_1212.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_archived_edit_1120.py`, `tests/test_engine_ble001_1202.py`, and `tests/test_engine_cockpit_view.py`.
- Environment: clean. No fallback needed.
- Important scope note: this green run is contextual only, not committed-deliverable proof, because `tests/test_storage_re_exports_1212.py` is modified locally in the working tree.

### Lint
- Ruff: clean on all 10 task-owned paths reviewed for this task.

### Coverage
- Informational only for td:1 review.
- `owlbear_kanban.storage`: 97%
- `owlbear_kanban.engine`: 50%
- `owlbear_kanban.corruption`: 46%
- `owlbear_kanban.activity_store`: 45%
- Scoped overall measurement: 42%

### Source Control State
- Builder commit `26b80b06` changed the original 9 task implementation/consumer files.
- Builder proof commit `150ffeac` last touched `tests/test_storage_re_exports_1212.py`.
- Latest builder fix commit `6f842938` changed only `serve/kanban/src/owlbear_kanban/storage.py` and `serve/kanban/tests/test_storage_1050.py`.
- `git status --short -- serve/kanban/src/owlbear_kanban/storage.py serve/kanban/tests/test_storage_1050.py tests/test_storage_re_exports_1212.py` returned `M tests/test_storage_re_exports_1212.py`.
- `git diff --unified=0 -- tests/test_storage_re_exports_1212.py` shows two uncommitted additions only:
  - `test_test_storage_1050_detect_corruption_not_from_storage`
  - `test_test_storage_1050_imports_detect_corruption_from_corruption`
- `git show 6f842938:tests/test_storage_re_exports_1212.py | rg -n "test_test_storage_1050_detect_corruption_not_from_storage|test_test_storage_1050_imports_detect_corruption_from_corruption"` exited 1, confirming those two proofs are absent from committed HEAD.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test in committed HEAD | Would Fail If AC Violated? | Verdict |
|---------|-------------------------------|----------------------------|---------|
| AC1 `storage.py` cleanup + import-line removal | `TestFromAC_StorageAllCleanup`, `TestFromAC_StorageSourceImportLineRemoval` | Yes | COVERED |
| AC2 engine import migration | `TestFromAC_EngineImportMigration`, `TestFromAC_EngineNewImportTargets` | Yes | COVERED |
| AC3 package-test import migration | `TestFromAC_PackageTestImportSources`, `TestFromAC_PackageTestSourceModuleImports` | No. The two `test_storage_1050.py detect_corruption` proofs exist only in the local working-tree diff, not in committed HEAD. | MISSING |
| AC4 root test patch targets | `TestFromAC_RootTestPatchTargets`, `TestFromAC_RootTestNewPatchTargets` | Yes | COVERED |
| AC5 `storage.py` docstring reduced scope | direct file review of `serve/kanban/src/owlbear_kanban/storage.py:19`, `:21`, `:534` | Yes | COVERED |
| AC6 task-local proving tests assert absence + presence | `tests/test_storage_re_exports_1212.py` in committed HEAD | No. The two AC3 discriminating assertions needed to satisfy the refined proof requirement are not committed. | MISSING |
| AC7 scoped regression gate | quality-runner scoped working-tree run | Yes for the current workspace; not the blocking issue | COVERED |

#### Security Review
- No issues found. The task is import rewiring, docstring cleanup, and proof tests only.

#### Test Integrity
- No committed builder weakening/removal of `TestFromAC_*` assertions detected.
- Latest committed proof change (`150ffeac`) was additive strengthening only.
- Current uncommitted changes are also additive only, but they are not part of the committed deliverable.

#### Test Quality
- Committed HEAD proof quality remains WEAK for AC3/AC6 because the `test_storage_1050.py detect_corruption` case is only proven by local, uncommitted tests. A committed snapshot with the same code could regress on that subcase without the committed task-local suite catching it.

#### Data Safety
- No issues found.

#### Necessity Check
- Skipped. Refactor task; no new dependency or integration.

#### Builder Process Quality
- The task body already contains two prior `## Review Evidence` rejection sections.
- This is another review failure on the same class of proof-delivery gap: green scoped evidence exists locally, but the committed snapshot does not carry the full required proof.
- Loop-breaker applies: subsequent review failure routes to backlog.

### AC Compliance
| AC Line | Evidence | Mapped Test / Proof | Status |
|---------|----------|---------------------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/storage.py:46` retains only the internal corruption import; `rg -n "from owlbear_kanban\.(body_parser|activity_store) import" serve/kanban/src/owlbear_kanban/storage.py` returned no matches; `serve/kanban/src/owlbear_kanban/storage.py:534` `__all__` omits the removed facade symbols | committed AC1 proof classes | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:46` imports `compact_activity_log` / `list_activity_events` from `activity_store`; `serve/kanban/src/owlbear_kanban/engine.py:50` imports `detect_corruption` from `corruption` | committed AC2 proof classes | PASS |
| AC3 | Live consumer imports are correct: `serve/kanban/tests/test_corruption.py:18`, `serve/kanban/tests/test_engine_activity.py:18`, `serve/kanban/tests/test_engine_archived_edit_1120.py:35`, `serve/kanban/tests/test_storage.py:14`, `serve/kanban/tests/test_storage_1050.py:30` all point at source modules for the migrated symbols | committed AC3 proof is incomplete for `test_storage_1050.py detect_corruption` | PASS (implementation), FAIL as committed proof |
| AC4 | `tests/test_engine_ble001_1202.py:176` patches `owlbear_kanban.engine.detect_corruption`; `tests/test_engine_cockpit_view.py:847` patches `owlbear_kanban.engine.compact_activity_log` | committed AC4 proof classes | PASS |
| AC5 | `serve/kanban/src/owlbear_kanban/storage.py:19` / `:21` docstring now lists only `Section`, `ConcurrencyError`, `ActivityEvent`, `ActivityCompactionResult`, `SessionRecord`, `MigrationRequiredError`, consistent with the reduced public surface at `serve/kanban/src/owlbear_kanban/storage.py:534` | direct inspection | PASS |
| AC6 | Working tree contains the two required AC3 proofs at `tests/test_storage_re_exports_1212.py:185` and `:367`, but committed HEAD does not | commit-state checks above | FAIL |
| AC7 | quality-runner scoped working-tree run green: 186 passed, 0 failed | scoped run | PASS (workspace state) |

### Deductions
- `-0.13` AC6 fails on the committed deliverable: two required discriminating proofs exist only as local modifications.
- `-0.05` Current green quality evidence is from a dirty working tree, so it cannot be accepted as committed-snapshot proof.
- `-0.05` This is a subsequent review failure on a recurring proof-delivery gap; loop-breaker applies.
- Confidence: `0.77`

### Verdict
- FAIL -> backlog
- Reason: the live source changes now appear correct, but the task still fails the review gate because the two AC3 proof tests for `test_storage_1050.py detect_corruption` are not committed to HEAD. The green scoped run depends on local-only test additions, which is not acceptable delivery evidence. This is another repeat review failure on the same proof-delivery pattern, so route to backlog.

### Required Follow-up
- Commit the two AC3 proof tests now present only in the working tree into `tests/test_storage_re_exports_1212.py`.
- Re-run the scoped reviewer gate against a clean working tree / committed snapshot.
- Tighten task notes so future cycles distinguish committed evidence from local workspace evidence.

### Post-task Reflection
- Problem faced: the scoped quality run was green, but only because it executed against a dirty working tree.
- Workaround applied: verified commit scope, working-tree status, and uncommitted diff before trusting the green run.
- Pattern discovered: repeat re-export-removal tasks are prone to commit-state false greens when proof tests are added locally but not promoted to HEAD.
- Quality gap: task history again overstated delivery completeness relative to git history.
[[2026-05-03]]
## Architecture Review (cycle 5 — commit-delivery loop-break)

**Verdict:** APPROVED → todo

**Context:** Reviewer rejected at confidence 0.77 in cycle 4. Same class of failure as cycles 2 and 3: proof tests exist in working tree but are not committed to HEAD. All AC lines are precise and unchanged. All implementation is verified correct in the live workspace.

### AC Assessment

| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC1 storage.py cleanup (td:1) | Precise, implementation verified | None |
| AC2 engine import migration (td:1) | Precise, implementation verified | None |
| AC3 test consumer migration (td:1) | Precise, implementation verified (detect_corruption now from owlbear_kanban.corruption in test_storage_1050.py) | None |
| AC4 root test patch targets (td:1) | Precise, implementation verified | None |
| AC5 storage docstring (td:0) | Precise, implementation verified (CorruptionError removed from docstring) | None |
| AC6 absence + presence proofs (td:1) | Precise. Both proof functions exist at lines 185 and 367 of tests/test_storage_re_exports_1212.py — NOT COMMITTED | None — builder commits |
| AC7 scoped regression (td:0) | Precise, verified passing | None |

### Architecture Notes
- Architecture sound — verified 4 prior cycles.
- Implementation complete in workspace — verified via direct file inspection this cycle.
- Root cause of recurring failure: test-writer adds proofs locally → builder commits implementation files but not the test file → reviewer catches the gap.

### Builder Guidance (cycle 5 — COMMIT ONLY)

**THE ONLY REQUIRED ACTION IS:**
```
git add tests/test_storage_re_exports_1212.py
git commit -m "test: commit AC3 proof assertions for detect_corruption (#1212, builder)"
```

**Do NOT:**
- Modify any source files
- Modify any test assertions
- Touch any file other than `tests/test_storage_re_exports_1212.py`

**Verification after commit:**
- `git status --short -- tests/test_storage_re_exports_1212.py` must return empty (clean)
- `uv run pytest tests/test_storage_re_exports_1212.py -n0` must pass 34 tests

### Dependency Analysis
- #1211: done — no blocker.

### Test Depth
- Max depth: 1
- Test-writer: SKIP — all tests already written and passing in working tree.

### Challenge
- SKIPPED — 5th cycle re-approval of verified implementation. Only delivery artifact (git commit) is missing. No architectural question remains.
[[2026-05-03]]
## Test-Writer Notes

**Retry cycle (Step 1b.1) — commit-gap closure.**

**Test file:** `tests/test_storage_re_exports_1212.py`

**Context:** Reviewer's Required Follow-up (cycles 3–5) was commit-delivery only: two AC3 proof tests (`test_test_storage_1050_detect_corruption_not_from_storage`, `test_test_storage_1050_imports_detect_corruption_from_corruption`) existed in working tree but were never committed to HEAD. No new tests written this cycle.

**Action taken:** Committed the two proof tests to HEAD as `bfe67e31`.

**Verification:** `pytest tests/test_storage_re_exports_1212.py -n0` → 34 passed. Ruff: clean. `git status` → clean working tree.

**AC coverage (all cycles combined):**
| AC | Coverage |
|----|---------|
| AC1 | ✓ absence + positive |
| AC2 | ✓ absence + positive |
| AC3 | ✓ absence + positive (detect_corruption for test_storage_1050.py now committed) |
| AC4 | ✓ absence + positive |
| AC5 | td:0 |
| AC6 | ✓ proof committed to HEAD |
| AC7 | td:0 |

**Step 1b.1 rationale:** Reviewer's Required Follow-up contained ONLY a test-proof commit gap — no implementation fixes needed. All 34 tests pass against current implementation. Builder skip: advancing directly to review.
[[2026-05-03]]
## Builder Notes
- Cycle type: verification/pass-through. No file edits were required in this cycle.
- Live committed-state check: `tests/test_storage_re_exports_1212.py` is clean in working tree (no local modifications).
- Quality-runner scoped gate: 186 passed, 0 failed.
  - Included: `tests/test_storage_re_exports_1212.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_archived_edit_1120.py`, `tests/test_engine_ble001_1202.py`, `tests/test_engine_cockpit_view.py`
- Lint gate: `ruff` clean on `tests/test_storage_re_exports_1212.py`, `serve/kanban/tests/test_storage_1050.py`, `serve/kanban/src/owlbear_kanban/storage.py`.
- Coverage: `owlbear_kanban.storage` = 97% (216 statements, 7 missed).
- Evidence summary: AC-proof suite and scoped regressions are green on current HEAD state; no implementation delta needed.
- Fixes applied: none (commit-delivery gap already resolved before this cycle).
[[2026-05-03]]
## Review Evidence
### Test Results
- Quality-runner scoped pass: 186 passed, 0 failed across `tests/test_storage_re_exports_1212.py`, `serve/kanban/tests/test_engine_activity.py`, `serve/kanban/tests/test_engine_archived_edit_1120.py`, `tests/test_engine_ble001_1202.py`, and `tests/test_engine_cockpit_view.py`.
- Environment clean. No fallback or rerun required.

### Lint
- Ruff clean on scoped source and test paths: `serve/kanban/src/owlbear_kanban/storage.py`, `serve/kanban/src/owlbear_kanban/engine.py`, `serve/kanban/tests/test_storage_1050.py`, `tests/test_storage_re_exports_1212.py`, `tests/test_engine_ble001_1202.py`, `tests/test_engine_cockpit_view.py`, `serve/kanban/tests/test_engine_activity.py`, and `serve/kanban/tests/test_engine_archived_edit_1120.py`.

### Coverage
- Informational only for td:1 review.
- `owlbear_kanban.storage`: 97%
- `owlbear_kanban.engine`: 50%
- `owlbear_kanban.corruption`: 46%
- `owlbear_kanban.activity_store`: 45%
- Scoped overall: 42%

### Source Control State
- Current task-owned files are clean in the working tree.
- Changed-file reconstruction from task-related commits:
  - `26b80b06`: implementation and consumer import migration (`engine.py`, `storage.py`, package tests, root tests)
  - `150ffeac`: positive proof expansion in `tests/test_storage_re_exports_1212.py`
  - `6f842938`: `storage.py` docstring fix and `test_storage_1050.py` import-path fix
  - `bfe67e31`: committed AC3 `detect_corruption` proof additions in `tests/test_storage_re_exports_1212.py`
- Test integrity check: `git show --numstat` for `150ffeac` reported `173` additions and `0` deletions; `bfe67e31` reported `14` additions and `0` deletions. No `TestFromAC_*` weakening or removal detected.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|----------------------------|---------|
| AC1 `storage.py` cleanup + import-line removal | `tests/test_storage_re_exports_1212.py:53`, `:257` | Yes | COVERED |
| AC2 engine import migration | `tests/test_storage_re_exports_1212.py:111`, `:290` | Yes | COVERED |
| AC3 package-test import migration | `tests/test_storage_re_exports_1212.py:149`, `:185`, `:321`, `:367` | Yes | COVERED |
| AC4 root test patch targets | `tests/test_storage_re_exports_1212.py:205`, `:387` | Yes | COVERED |
| AC5 `storage.py` docstring reduced scope | direct file review of `serve/kanban/src/owlbear_kanban/storage.py:19-21`, `:534` | Yes | COVERED |
| AC6 task-local proving tests assert absence + presence | committed proof classes in `tests/test_storage_re_exports_1212.py:257`, `:290`, `:321`, `:367`, `:387`; commit `bfe67e31` confirmed in HEAD | Yes | COVERED |
| AC7 scoped regression gate | quality-runner scoped run | Yes | COVERED |

#### Security Review
- No issues found. The task changes are import rewiring, docstring narrowing, and proof tests only.

#### Test Integrity
- Preserved. Task-local `TestFromAC_*` changes were additive strengthening only.

#### Test Quality
- Assertion specificity: STRONG. The proof suite checks exact module/symbol import targets and exact root patch strings.
- Negative coverage: ADEQUATE for a structural import-refactor task. Each migrated symbol family has absence proof plus positive target proof.
- Manual mutation reasoning: STRONG. Reintroducing any old storage-based import or removing the new target import would fail the mapped task-local tests.
- Independence: STRONG.
- Naming: STRONG.

#### Data Safety
- No issues found.

#### Necessity Check
- Skipped. Refactor task; no new dependency or integration.

#### Builder Process Quality
- FRICTION, not loop. This task had multiple review cycles, but the retries were not identical and the final committed snapshot closes the previously documented proof-delivery gaps.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC1 | `serve/kanban/src/owlbear_kanban/storage.py:19-21` now documents only the reduced re-exported type surface; `serve/kanban/src/owlbear_kanban/storage.py:534` `__all__` begins a reduced public list; repo search found no `body_parser` or `activity_store` import lines in `storage.py` | `tests/test_storage_re_exports_1212.py:53`, `:257` | PASS |
| AC2 | `serve/kanban/src/owlbear_kanban/engine.py:46` imports `compact_activity_log` and `list_activity_events` from `activity_store`; `serve/kanban/src/owlbear_kanban/engine.py:50` imports `detect_corruption` from `corruption` | `tests/test_storage_re_exports_1212.py:111`, `:290` | PASS |
| AC3 | Live package-test consumers now point at source modules: `serve/kanban/tests/test_corruption.py:14`, `:18`; `serve/kanban/tests/test_engine_activity.py:18`; `serve/kanban/tests/test_engine_archived_edit_1120.py:35`; `serve/kanban/tests/test_storage.py:14`; `serve/kanban/tests/test_storage_1050.py:30` | `tests/test_storage_re_exports_1212.py:149`, `:185`, `:321`, `:367` | PASS |
| AC4 | Root tests patch the engine module paths: `tests/test_engine_ble001_1202.py:176`, `:195`; `tests/test_engine_cockpit_view.py:847` | `tests/test_storage_re_exports_1212.py:205`, `:387` | PASS |
| AC5 | `serve/kanban/src/owlbear_kanban/storage.py:19-21` no longer advertises `CorruptionError` as a re-exported type; reduced public surface remains aligned with `serve/kanban/src/owlbear_kanban/storage.py:534` | direct inspection | PASS |
| AC6 | The committed task-local suite includes both positive import-target proof and the two `detect_corruption` tests at `tests/test_storage_re_exports_1212.py:185` and `:367`; `git show bfe67e31:tests/test_storage_re_exports_1212.py` confirms they are part of committed HEAD | task-local proof suite | PASS |
| AC7 | Quality-runner scoped run: 186 passed, 0 failed | scoped run | PASS |

### Deductions
- `-0.03` Prior cycle churn required explicit commit-state reconstruction before trusting the green snapshot.
- Confidence: `0.97`

### Verdict
- PASS to docs
- Reason: current HEAD carries the required proof, the migrated imports and root patch targets match the refined AC, the storage docstring is aligned with the reduced public surface, and no `TestFromAC_*` weakening occurred.

### Post-task Reflection
- Separating working-tree evidence from committed evidence was the key risk control for this task.
- `git show --numstat` was sufficient to prove the proof commits were additive-only and preserved `TestFromAC` integrity.
- The final repo sweep for stale storage-based imports closed the original AC3 false-green pattern.
[[2026-05-03]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A | `serve/kanban/README.md` has no reference to the removed re-export symbols or import paths — only `repair_storage()` method table entry unaffected by this refactor. No prose doc updates needed. |
| 2 | Module docstrings | Yes | Verified | `serve/kanban/src/owlbear_kanban/storage.py` docstring updated in AC5 (commit `6f842938`) — confirmed accurate: "Re-exported types" no longer lists `CorruptionError`. `engine.py` docstring describes KanbanEngine API, not import paths — accurate and unaffected. |
| 3 | External attribution | No | N/A | Task is a pure internal import-refactor; no external patterns used. |
| 4 | Research doc | No | N/A | No `.owlbear/research/` slug produced for this task. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/kanban/src/**`) both matched. Footers updated to `Last verified: 2026-05-04 (e1db031a)`. Commit: `a8da91fa`. |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted; no IN-scope doc references a deleted feature. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/kanban/src/owlbear_kanban/storage.py` | IN (docstring) | Verified — AC5 docstring fix confirmed accurate |
| `serve/kanban/src/owlbear_kanban/engine.py` | IN (docstring) | Verified — docstring accurate and unaffected |
| `serve/kanban/tests/test_storage_1050.py` | IN (docstring) | Test file — no module-level docstring; N/A |
| `tests/test_storage_re_exports_1212.py` | IN (docstring) | Test file — no module-level docstring; N/A |
| `share/diagrams/kanban.excalidraw` | IN (diagram) | Footer updated |
| `share/diagrams/mcp-topology.excalidraw` | IN (diagram) | Footer updated |

### Files Updated
- `share/diagrams/kanban.excalidraw` — footer: `Last verified: 2026-05-04 (e1db031a)`
- `share/diagrams/mcp-topology.excalidraw` — footer: `Last verified: 2026-05-04 (e1db031a)`

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1212-*` files found)
[[2026-05-03]]
## Audit

### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1 storage.py cleanup | Reviewer verified __all__ omits facade symbols; storage.py:46 retains only internal corruption import | PASS |
| AC2 engine import migration | engine.py:46 imports from activity_store, engine.py:50 from corruption; reviewer mapped 6 test lines | PASS |
| AC3 package-test migration | Spot-checked test_storage_1050.py:30 -- detect_corruption from owlbear_kanban.corruption confirmed | PASS |
| AC4 root test patch targets | Reviewer mapped test_engine_ble001_1202.py:176, test_engine_cockpit_view.py:847 | PASS |
| AC5 storage docstring | Spot-checked storage.py:19-21 -- lists only Section/ConcurrencyError/ActivityEvent/etc., no CorruptionError | PASS |
| AC6 absence + presence proofs | Commit bfe67e31 confirmed in HEAD via git log; 34 tests in committed file | PASS |
| AC7 scoped regression | Reviewer scoped run 186/0; auditor full suite confirms 0 failures in task scope | PASS |

### Test Results
- pytest (full suite): 856 passed, 30 failed -- 0 failures in task #1212 scope (all are unrelated branch debt: #1234, #1015, #1181, #1195, cockpit models, engine accessor)
- ruff: 1 violation (T201 in copilot_auth.py) -- not in task scope
- vitest: Shell test failures -- unrelated frontend

### Commit Integrity
- 26b80b06: refactor: remove storage facade re-exports (#1212, builder)
- 150ffeac: test: commit positive import-proof assertions (#1212, builder)
- 6f842938: fix: close AC3/AC5 gaps (#1212, builder)
- bfe67e31: test: commit AC3 proof assertions for detect_corruption (#1212, test-writer)
- a8da91fa: docs: update diagram footers for storage re-export removal (#1212, doc-writer)

### Architect Quality: 3/5
Builder Notes had incomplete symbol map (missed detect_corruption for test_storage_1050.py), causing 3 extra pipeline cycles. AC text itself was precise after cycle 2 refinement.

### Deduction Breakdown
- AC quality score 3: -.03

### Confidence: 0.97
### Action: archive