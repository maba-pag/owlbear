---
id: 1109
title: Add exists-guard to mode-6 rename in attempt_repair
status: archived
priority: medium
created: 2026-04-23T00:10:27.649126+00:00
updated: 2026-04-23T16:51:16.338664+00:00
tags:
- scope:kanban
- tdd:red
parent:
depends_on:
- 1108
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

See `.owlbear/research/1108-mode6-rename-collision-guard.md`.

`attempt_repair` mode-6 (ID/filename mismatch) calls `path.replace(new_path)` without checking if `new_path` already exists. `Path.replace()` silently overwrites the destination, causing data loss of a valid task file.

## Acceptance Criteria

- [ ] AC-1: When mode-6 repair target path already exists, the corrupt file is quarantined instead of overwriting the existing file.
- [ ] AC-2: `RepairOutcome` has `action="quarantined"` with detail mentioning "rename collision".
- [ ] AC-3: The existing destination file is untouched after the collision guard triggers.
- [ ] AC-4: Happy-path mode-6 rename (no collision) continues to work as before.

## Implementation Guidance

In `serve/kanban/src/owlbear_kanban/corruption.py`, mode-6 block (~L390), before `path.replace(new_path)`:

```python
if new_path.exists():
    return _quarantine()
```

The quarantine detail should mention "rename collision" for diagnosability.

## Test Guidance

Add test in `serve/kanban/tests/test_corruption.py`:
- Create valid `42-my-task.md` + corrupt `999-wrong.md` (frontmatter id: 42).
- Call `attempt_repair(corrupt_file, ERR_CORRUPT_ID_FILENAME_MISMATCH, config)`.
- Assert outcome is quarantined, valid file untouched, corrupt file in quarantine/.

[[2026-04-23]]
## Research
- Research doc: .owlbear/research/1108-mode6-rename-collision-guard.md (validation pass — existing doc from #1108 covers this task)
- Sources: 6 studied (all codebase), 3 high-relevance
- Recommendation: Option A (exists-guard + quarantine), confidence: 0.90
- Follow-up tasks created: none — this IS the follow-up from #1108
- Decision requests: none

### Validation Findings
1. Bug confirmed at corruption.py:394 — `path.replace(new_path)` still has no existence check
2. `_quarantine()` closure (L323) has no custom-detail parameter. AC-2 requires "rename collision" in the detail. Builder must either (a) add optional `detail` param to `_quarantine()`, or (b) inline the quarantine+outcome logic for the collision branch. Option (b) is simpler — ~6 lines, avoids touching the shared helper.
3. Happy-path mode-6 test exists in test_storage_1050.py:972; no collision test exists anywhere.
4. Dependency #1108 is satisfied (archived).

### Tier Classification
T1 — autonomous bug fix. No architecture change, no new capability, no security implications.

## Challenge Results
- Challenger: SKIPPED — trivial single-option bug fix, no design ambiguity (same rationale as #1108 research doc)
[[2026-04-23]]
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One bug fix: exists-guard on mode-6 rename |
| Interface clarity | PASS | AC-1–4 all independently verifiable; RepairOutcome contract clear |
| Dependency correctness | PASS | #1108 archived (done) |
| Module layering | PASS | Single-file change in corruption.py, same module |
| TDD compliance | PASS | Tagged tdd:red; test guidance provided |
| KISS/YAGNI | PASS | 3–6 LOC change, no over-engineering |
| Premise challenge | PASS | Bug confirmed: Path.replace() silently overwrites at corruption.py:394 |
| Pattern consistency | PASS | Follows existing quarantine pattern in same function |
| Security surface | PASS | Fixes data-loss bug; no new boundaries |
| Single domain | PASS | kanban domain only |

### Failure Mode Map
| Codepath | Failure Mode | Exception | Handled? | User Impact |
|----------|-------------|-----------|----------|-------------|
| mode-6 rename | new_path already exists (collision) | None — guard returns quarantine | Yes (this fix) | Corrupt file quarantined, valid file preserved |
| mode-6 rename | new_path does not exist (happy path) | OSError from path.replace() | Yes (existing except block) | Rename succeeds or RepairOutcome action=failed |

### AC Assessment
| AC Line | Assessment | Action |
|---------|-----------|--------|
| AC-1: collision → quarantine | Verifiable, testable | None |
| AC-2: detail mentions "rename collision" | Verifiable; _quarantine() lacks custom detail — validation findings correctly instruct builder to inline (option b) | None — implementation guidance pseudocode is advisory, validation findings resolve |
| AC-3: existing file untouched | Verifiable with file-content assertion | None |
| AC-4: happy-path unchanged | Verifiable; existing test at test_storage_1050.py:972 provides regression baseline | None |

### Challenge Results
- Challenger: reconsider (0.71)
- Challenges raised: (1) quarantine path also uses replace, (2) detail-contract ambiguity, (3) AC-4 evidence thin, (4) lock inconsistency
- Architect response: REBUTTED — (1) out of scope per research doc, low risk; (2) AC-2 specifies outcome, validation findings resolve implementation; (3) existing test sufficient for regression; (4) YAGNI for single-user tool
- Final confidence: 0.88

### Verdict: APPROVE
### Action Taken: Advanced to todo. No AC changes needed — all 4 lines verifiable, implementation guidance supported by validation findings.
[[2026-04-23]]
## Test-Writer Notes

**Test file:** `tests/test_mode6_rename_collision_guard_1109.py`
**Class:** `TestFromAC_Mode6CollisionGuard`
**Total:** 10 tests — 5 FAIL (new collision-guard behavior), 5 PASS (regression guards)

### Results by category

| Category | Count | Tests |
|----------|-------|-------|
| Happy-path collision (new behavior) | 2 | AC-1 quarantine action, AC-1 file moved to quarantine/ |
| Error/outcome fields (new behavior) | 2 | AC-2 action='quarantined', AC-2 detail contains 'rename collision' |
| Integrity guard (new behavior) | 1 | AC-3 destination file content untouched |
| Regression guards (existing behavior) | 5 | AC-1 no-collision contrast, AC-4 ×4 |

### AC coverage

| AC | Tests | Notes |
|----|-------|-------|
| AC-1: collision → quarantine | `test_ac1_collision_quarantines_corrupt_file`, `test_ac1_collision_corrupt_file_moved_to_quarantine_dir`, `test_ac1_no_collision_does_not_quarantine` | 2 fail + 1 regression guard (no-collision contrast passes in RED by design) |
| AC-2: action='quarantined', detail mentions 'rename collision' | `test_ac2_quarantine_outcome_action_is_quarantined`, `test_ac2_detail_mentions_rename_collision` | 2 fail |
| AC-3: existing destination untouched | `test_ac3_existing_destination_file_content_untouched` | 1 fail |
| AC-4: happy path unchanged | `test_ac4_happy_path_no_collision_returns_fixed`, `test_ac4_happy_path_renamed_file_exists`, `test_ac4_happy_path_original_file_gone`, `test_ac4_happy_path_outcome_task_id_is_frontmatter_id` | 4 regression guards — pass in RED by design (existing behavior preserved) |

**Ruff:** clean.

**Note on passing tests:** The 5 passing tests are regression guards for existing behavior (AC-4 happy path + AC-1 no-collision contrast). They test that the fix must not break the already-working rename path. These pass in RED by design — they will catch accidental regressions in GREEN.
[[2026-04-23]]
## Builder Notes
- Implementation: added mode-6 rename collision guard in serve/kanban/src/owlbear_kanban/corruption.py before `path.replace(new_path)`.
- Behavior: when the computed rename destination already exists, the corrupt source file is quarantined (no overwrite), and `RepairOutcome` returns `action="quarantined"` with detail containing `rename collision` plus quarantine destination.
- Files changed: serve/kanban/src/owlbear_kanban/corruption.py
- Tests (task-scoped): `tests/test_mode6_rename_collision_guard_1109.py` -> 10 passed.
- Regression check: `serve/kanban/tests/test_storage_1050.py -k mode6_id_filename_mismatch_renames` -> 1 passed.
- Durable module check: `serve/kanban/tests/test_corruption.py` -> 61 passed.
- Coverage: 83% on `owlbear_kanban.corruption` using durable module test run.
- Ruff: clean for touched source and task test paths.
- Evidence summary: collision path now quarantines and preserves existing destination file content; happy-path rename behavior remains unchanged.
- Reflection:
  - Problem faced: mode-6 branch used direct `Path.replace` without preflight destination check.
  - Workaround applied: inserted explicit `new_path.exists()` guard and collision-specific quarantine outcome.
  - Pattern discovered: keep shared `_quarantine()` helper unchanged when AC needs branch-specific detail; inline only the specialized path.
  - Quality gap: module-level coverage remains below 90% baseline (83%) despite all relevant tests passing for this task.

[[2026-04-23]]
## Review Evidence
### Test Results
- Task-owned suite via quality-runner: 10 passed, 0 failed, 0 skipped (`tests/test_mode6_rename_collision_guard_1109.py`).
- Combined regression scope via quality-runner: 124 passed, 0 failed, 0 skipped (`tests/test_mode6_rename_collision_guard_1109.py`, `serve/kanban/tests/test_corruption.py`, `serve/kanban/tests/test_storage_1050.py`).

### Lint: clean
- quality-runner reported clean on `serve/kanban/src/` and `tests/test_mode6_rename_collision_guard_1109.py`.

### Coverage: `owlbear_kanban.corruption` = 90%
- quality-runner combined scope (`tests/test_mode6_rename_collision_guard_1109.py` + `serve/kanban/tests/test_corruption.py` + `serve/kanban/tests/test_storage_1050.py`) reported `owlbear_kanban.corruption` at 90%.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC-1: collision quarantines instead of overwriting | `test_ac1_collision_quarantines_corrupt_file`, `test_ac1_collision_corrupt_file_moved_to_quarantine_dir`, `test_ac1_no_collision_does_not_quarantine` | Yes. If the guard at `serve/kanban/src/owlbear_kanban/corruption.py:393-404` were removed and overwrite resumed, assertions at `tests/test_mode6_rename_collision_guard_1109.py:128`, `:142-145`, and `:156` would fail. | COVERED |
| AC-2: outcome is `quarantined` and detail mentions `rename collision` | `test_ac2_quarantine_outcome_action_is_quarantined`, `test_ac2_detail_mentions_rename_collision` | Yes. Assertions at `tests/test_mode6_rename_collision_guard_1109.py:173` and `:186` directly pin the action/detail produced by `serve/kanban/src/owlbear_kanban/corruption.py:399-404`. | COVERED |
| AC-3: existing destination file remains untouched | `test_ac3_existing_destination_file_content_untouched` | Yes. If collision handling still overwrote the destination, assertions at `tests/test_mode6_rename_collision_guard_1109.py:206-207` would fail. | COVERED |
| AC-4: happy-path rename still works | `test_ac4_happy_path_no_collision_returns_fixed`, `test_ac4_happy_path_renamed_file_exists`, `test_ac4_happy_path_original_file_gone`, `test_ac4_happy_path_outcome_task_id_is_frontmatter_id`, plus existing regression `test_attempt_repair_mode6_id_filename_mismatch_renames` | Yes. The non-collision path remains at `serve/kanban/src/owlbear_kanban/corruption.py:416-422`, and the assertions at `tests/test_mode6_rename_collision_guard_1109.py:223`, `:236`, `:248`, `:260`, plus `serve/kanban/tests/test_storage_1050.py:972-985`, would fail if rename behavior regressed. | COVERED |

#### Security Review
- No issues found. The change is a local filesystem guard in `attempt_repair`; it adds no new dependencies, no user-controlled command execution, no deserialization, and no path construction outside existing `make_task_filename(...)` / `move_to_quarantine(...)` flows. The quarantine helper still enforces containment at `serve/kanban/src/owlbear_kanban/storage.py:524-531`.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| `TestFromAC_Mode6CollisionGuard` method set documented in `## Test-Writer Notes` | Current file still contains the same 10 AC-named methods at `tests/test_mode6_rename_collision_guard_1109.py:115`, `:130`, `:147`, `:160`, `:175`, `:192`, `:213`, `:225`, `:238`, `:250`; current assertions remain direct and specific at `:128`, `:142-145`, `:186`, `:206-207`, `:223`, `:236`, `:248`, `:260`. | PRESERVED |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | STRONG | Direct equality / substring / file-existence / byte-for-byte content assertions at `tests/test_mode6_rename_collision_guard_1109.py:128`, `:142-145`, `:186`, `:206-207`, `:223`, `:236`, `:248`, `:260`. |
| Negative/error-path coverage | ADEQUATE | Task suite covers collision and no-collision branches; helper behavior is also covered in `serve/kanban/tests/test_storage_1050.py:413-474`. The two defensive exception wrappers in `serve/kanban/src/owlbear_kanban/corruption.py:407-413` and `:424-430` are not directly simulated. |
| Manual mutation reasoning | STRONG | Removing `if new_path.exists()` or changing the collision detail/action would immediately fail `tests/test_mode6_rename_collision_guard_1109.py:128`, `:142-145`, `:173`, `:186`, `:206-207`. |
| Test independence | STRONG | Each test builds its own tmp board via `_make_board(...)`; no shared mutable state is reused. |
| Descriptive test names | STRONG | Method names encode the AC and behavior under test (`test_ac1_*`, `test_ac2_*`, `test_ac3_*`, `test_ac4_*`). |

#### Data Safety
- No new issue found. The change removes the prior overwrite hazard by checking `new_path.exists()` before `path.replace(new_path)` and quarantining instead (`serve/kanban/src/owlbear_kanban/corruption.py:393-404`). Existing destination preservation is proven by `tests/test_mode6_rename_collision_guard_1109.py:206-207`.

#### Implementation-Aware Gaps
- No significant untested paths found for this task. The new collision branch, quarantine movement, detail text, destination preservation, and unchanged happy path are all exercised. The uncovered exception wrappers in `serve/kanban/src/owlbear_kanban/corruption.py:407-413` and `:424-430` are defensive wrappers around existing filesystem operations and do not undermine AC proof.

#### Builder Process Quality
| Metric | Value |
|--------|-------|
| Builder Notes sections | 1 |
| Existing `## Review Evidence` sections before this note | 0 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Task-owned tests alone only covered 30% of `owlbear_kanban.corruption`; module-level gating required the durable corruption suite plus the pre-existing mode-6 storage regression to reach 90%. That broader scope is the correct review evidence for this module.
- The touched module passes the coverage floor exactly, not with buffer.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| AC-1 | Guard added at `serve/kanban/src/owlbear_kanban/corruption.py:393`; collision return quarantines at `:396-404`; task tests assert `action == "quarantined"` and physical move to `quarantine/` at `tests/test_mode6_rename_collision_guard_1109.py:128`, `:142-145`. | `test_ac1_collision_quarantines_corrupt_file`, `test_ac1_collision_corrupt_file_moved_to_quarantine_dir` | PASS |
| AC-2 | Collision detail string contains `rename collision` in `serve/kanban/src/owlbear_kanban/corruption.py:403-404`; task tests assert action and detail at `tests/test_mode6_rename_collision_guard_1109.py:173`, `:186`. | `test_ac2_quarantine_outcome_action_is_quarantined`, `test_ac2_detail_mentions_rename_collision` | PASS |
| AC-3 | Collision path avoids `path.replace(new_path)` and instead quarantines (`serve/kanban/src/owlbear_kanban/corruption.py:393-404`); destination preservation asserted byte-for-byte at `tests/test_mode6_rename_collision_guard_1109.py:206-207`. | `test_ac3_existing_destination_file_content_untouched` | PASS |
| AC-4 | Happy-path rename remains in `serve/kanban/src/owlbear_kanban/corruption.py:416-422`; task tests assert fixed outcome, renamed file exists, original file gone, and task id equals frontmatter id at `tests/test_mode6_rename_collision_guard_1109.py:223`, `:236`, `:248`, `:260`; legacy regression still passes at `serve/kanban/tests/test_storage_1050.py:972-985`. | `test_ac4_happy_path_no_collision_returns_fixed`, `test_ac4_happy_path_renamed_file_exists`, `test_ac4_happy_path_original_file_gone`, `test_ac4_happy_path_outcome_task_id_is_frontmatter_id`, `test_attempt_repair_mode6_id_filename_mismatch_renames` | PASS |

### Deductions
- -0.03: module-level coverage required broader durable suites beyond the task-owned file to reach the 90% gate.
- -0.03: the new defensive exception wrapper for collision-quarantine failure is not directly simulated end-to-end.

### Confidence: 0.91
### Verdict: PASS

### Reflection
- Task-owned green tests were not sufficient to judge the touched module; the broader mode-6 regressions were necessary to establish coverage and preserve the happy path.
- The builder kept the change surgical in one source branch and did not weaken the AC-named task tests.
- Future mode-6 changes should add an explicit filesystem-failure simulation if they expand the collision-specific error contract further.
[[2026-04-23]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | Yes | N/A — no update needed | `serve/kanban/README.md` references `repair_storage()` as "Quarantine corrupt task files and create action-required tasks" — still accurate. Mode-6 collision guard is an internal implementation detail; the public surface description is unchanged. |
| 2 | Module docstrings | Yes | Verified — no update needed | `attempt_repair` docstring at L303–316 says "Auto-fixes are applied for modes 3, 4, 6 (rename file), 9. Non-fixable modes quarantine the file." Still accurate — mode 6 quarantines on collision, which is a non-fixable scenario. `Returns` already lists `action='quarantined'`. |
| 3 | External attribution | No | N/A | Research notes: "6 studied (all codebase), 3 high-relevance" — all internal sources. No external patterns used. |
| 4 | Research doc | Yes | Verified — exists | `.owlbear/research/1108-mode6-rename-collision-guard.md` confirmed present. Task body links it explicitly. |
| 5 | Diagram maintenance (describes match) | Yes | Updated | `share/diagrams/kanban.excalidraw` (describes: `serve/kanban/src/**`) and `share/diagrams/mcp-topology.excalidraw` (describes: `serve/kanban/src/**`) both matched. Footers updated from `3946c139` → `e2d8fb9e`. Committed as `2e4b9d73`. |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body. |
| 7 | Deletion detection | No | N/A | No files deleted. Only `serve/kanban/src/owlbear_kanban/corruption.py` modified and `tests/test_mode6_rename_collision_guard_1109.py` added. |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| serve/kanban/src/owlbear_kanban/corruption.py | IN (docstrings) | Verified — no docstring update needed |
| tests/test_mode6_rename_collision_guard_1109.py | OUT (test file) | N/A |
| share/diagrams/kanban.excalidraw | IN (diagram) | Footer updated |
| share/diagrams/mcp-topology.excalidraw | IN (diagram) | Footer updated |

### Files Updated
- share/diagrams/kanban.excalidraw (footer: 3946c139 → e2d8fb9e)
- share/diagrams/mcp-topology.excalidraw (footer: 3946c139 → e2d8fb9e)

### Child Tasks Created
- None

### Scratch Files Cleaned
- None found
[[2026-04-23]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC-1: collision → quarantine | Guard at `corruption.py:393`; tests at `test_mode6_rename_collision_guard_1109.py:128`, `:142-145` | PASS |
| AC-2: action='quarantined', detail mentions 'rename collision' | `corruption.py:399-404`; tests at `test_mode6_rename_collision_guard_1109.py:173`, `:186` | PASS |
| AC-3: existing destination untouched | Collision path avoids `path.replace`; test at `test_mode6_rename_collision_guard_1109.py:206-207` | PASS |
| AC-4: happy-path unchanged | `corruption.py:416-422`; tests at `test_mode6_rename_collision_guard_1109.py:223`, `:236`, `:248`, `:260`; legacy at `test_storage_1050.py:972` | PASS |

### Test Results
- pytest (full suite): 1358 passed, 121 failed, 4 skipped
- Task-scope failures: **0** — all 121 failures in unrelated modules (mcp-kanban models, cockpit, yaml loader, sessions, ideation diagram)
- ruff: 5 W292 violations — all outside task scope (test_deny_non_doc_writes, test_ideation_overhaul_static, test_setup_init_hook_conflicts, test_setup_init_settings, test_write_guard_hooks)

### Architect Quality: 4/5
All 4 AC lines specific and independently verifiable. Minor gap: `_quarantine()` detail mechanism needed builder decision (inline vs. param modification), resolved by validation findings during research phase. Implementation guidance was clear and matched final implementation.

### Deduction Breakdown
| Criterion | Applies? | Deduction |
|-----------|----------|-----------|
| AC line with no specific evidence | No — all 4 have test + code evidence | 0 |
| Lint violations | No — all 5 outside task scope | 0 |
| AC quality score ≤ 3 | No — score is 4/5 | 0 |
| Missing reviewer evidence section | No — present and detailed (PASS at 0.91) | 0 |
| Full-suite test failures in task scope | No — 0 in corruption module | 0 |

### Confidence: 1.00
### Action: archive

### Notes
- Reviewer evidence was thorough with detailed AC mapping, mutation reasoning, and security review. Trusted code-level findings.
- 121 background test failures are pre-existing debt across mcp-kanban, cockpit, yaml loader, and ideation modules — not introduced by this task.
- Commit verification limited to pipeline evidence (no terminal access); builder and doc-writer commit records are internally consistent.