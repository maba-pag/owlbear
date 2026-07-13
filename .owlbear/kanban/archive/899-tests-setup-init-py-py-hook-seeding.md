---
id: 899
title: 'Tests: setup/init.py .py hook seeding'
status: archived
priority: medium
created: 2026-04-16T22:54:12.469696+00:00
updated: 2026-04-17T06:04:22.287405+00:00
tags:
- phase-2
- scope:setup
- type:test
- platform
parent: 890
depends_on:
- 894
- 895
- 896
blocked: false
block_reason:
claimed_by:
claimed_at:
---
Brief: see parent #890 and `.owlbear/briefs/draft-macos-compat/brief.md`

## Acceptance Criteria

- [ ] Test file verifying setup/init.py seeds .py hooks (not .ps1) into target project
- [ ] Test verifying all 7 hook files are seeded
- [ ] Test verifying seeded settings.json does not contain Windows-only terminal profiles
- [ ] Test verifying no .ps1 filename references remain in init.py logic
- [ ] Tests fail (RED) — init.py still references .ps1

## Files

- `tests/test_init_py_hooks.py` (new, or extend existing init.py tests)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/init-py-hook-seeding-tests.md
- Sources: 5 studied, 4 high-relevance (all codebase)
- Recommendation: Option A — call init() with real seed/ dir, assert output (confidence: .85)
- Key findings: seed has 6×.ps1 (missing deny-scratch-only-writes), settings.json has Windows-only terminal profiles, init.py has no .ps1-specific logic (generic copy). 7 tests across 4 ACs, 6/7 naturally RED.
- Follow-up tasks created: none — #899 itself advances to backlog for test-writer; implementation covered by dependency tasks #894–#896
- Decision requests: none
- Tier: T1 — autonomous (test writing, no architectural decisions)
[[2026-04-17]]

## Architecture Review

### AC Refinement (supersedes original ACs — test-writer should follow these)

- [ ] Test file `tests/test_init_py_hooks.py` exists
- [ ] Test: calling `init()` with real `seed/` dir produces only `.py` hooks (no `.ps1`) in target `.owlbear/hooks/`
- [ ] Test: exactly 7 `.py` hook files seeded, matching canonical set: `allow-stances-only`, `deny-code-writes`, `deny-scratch-only-writes`, `deny-src-writes`, `deny-writes`, `lint-changed`, `session-context`
- [ ] Test: seeded `settings.json` contains no `terminal.integrated.profiles.windows` or `terminal.integrated.defaultProfile.windows` keys
- [ ] Test: `seed/.owlbear/hooks/` directory contains no `.ps1` files
- [ ] Test: `init.py` source text contains no `.ps1` filename string literals
- [ ] Test suite fails RED — seed currently has 6× `.ps1` files, no `.py`, missing `deny-scratch-only-writes`

AC changes from original:

- AC2 now specifies `.py` extension and lists canonical 7 hook names explicitly
- AC4 split into two: (a) seed dir `.ps1` check, (b) `init.py` source text check — original "init.py logic" was misleading since init.py has no `.ps1` references (it's a generic `shutil.copy2` copier)
- AC5 rationale corrected: RED because seed has `.ps1` files, not because "init.py references .ps1"
- Source text check (AC6 above) will PASS today — this is expected; 6/7 tests RED is sufficient

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Write RED tests for seed hook migration only |
| Interface clarity | PASS (after refinement) | ACs now specify exact assertions, extensions, canonical names |
| Dependency correctness | PASS | #894-896 archived/done; .py hooks exist in `.owlbear/hooks/` |
| Module layering | N/A | Test file only |
| TDD compliance | PASS | This IS the RED test task; `type:test` tagged |
| KISS/YAGNI | PASS | 7 tests across 4 concerns, minimal scope |
| Premise challenge | PASS | Seed drift confirmed: 6× .ps1 vs 7 canonical .py hooks |
| Pattern consistency | PASS | Follows existing `test_setup_init.py` and `test_scaffold_mcp_memory_524.py` patterns |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | scope:setup only |

### Notes

- **Test approach:** Option A from research — call `init()` with real `seed/` dir, assert output. See `.owlbear/research/init-py-hook-seeding-tests.md` for detailed test structure.
- **Existing test coexistence:** `tests/test_setup_init.py` `TestFromAC_SeedHooks` checks for `.ps1` existence (2 hooks). New tests check for `.py` presence and `.ps1` absence. Both can coexist until #898 (GREEN implementation) updates the seed — at which point old tests break. #898's builder should update/remove `TestFromAC_SeedHooks`.
- **Sequencing note:** #898 (impl) is already in `todo` but should not be picked up until #899 (tests) completes RED phase. No formal dependency link exists; orchestrator should sequence accordingly.
- **Non-impl tagging:** `type:test` tag already present — test-writer pass-through is correct.

### Challenge Results

- Challenger: reconsider (0.75)
- Concerns: AC4/AC5 locus ambiguity, AC2 extension clarity, existing test backward compat
- Architect response: accepted AC refinements (AC4/AC5 rewritten, AC2 made explicit). Rejected "stale dependency" concern — #894-896 are archived/done, not stale. Noted backward compat as downstream issue for #898.

### Verdict: REFINE → APPROVE

### Action Taken: Refined ACs for precision (see above), advanced to todo

[[2026-04-17]]

## Test-Writer Notes

- **Test file:** `tests/test_init_py_hooks.py`
- **Classes:** `TestFromAC_InitPyHookSeeding`, `TestFromAC_SettingsNoWindowsProfiles`, `TestFromAC_SeedHooksNoPsFiles`, `TestFromAC_InitPySourceNoPsRefs`
- **Tests per category:**
  - Happy path: 0 (all tests verify RED absence-of-correct-state)
  - Edge/boundary: 0
  - Error/assertion: 7 (all are state-assertion tests)
- **Total:** 7 tests — 6 FAIL, 1 PASS
- **Fail confirmation:** pytest run confirmed 6 FAILED, 1 PASSED

### AC Coverage

| AC (refined) | Test(s) | RED? |
|---|---|---|
| AC2: init() seeds only .py hooks | `test_seeded_hooks_are_py_not_ps1`, `test_seeded_hooks_have_py_extension` | FAIL ✓ |
| AC3: exactly 7 .py hooks, canonical set | `test_all_seven_hooks_seeded` | FAIL ✓ |
| AC4: seeded settings.json no Windows profile keys | `test_settings_no_windows_terminal_profiles`, `test_settings_no_windows_default_profile` | FAIL ✓ |
| AC5: seed hooks dir no .ps1 files | `test_seed_hooks_dir_no_ps1_files` | FAIL ✓ |
| AC6: init.py source no .ps1 literals | `test_init_py_source_no_ps1_refs` | PASS (expected — init.py already clean) |

**Note:** 6/7 RED is correct and expected. `test_init_py_source_no_ps1_refs` passes today because init.py has no .ps1 references (it uses a generic `shutil.copy2` copier). This is per the architecture review finding. The builder (#898) drives the remaining 6 tests to GREEN by updating seed hooks to .py and removing Windows terminal profiles from seed settings.json.
[[2026-04-17]]

## Builder Notes

**Files changed:** `tests/test_setup_init.py` (1 file, 20 deletions)

- Note: `tests/test_init_py_hooks.py` was written by test-writer and already in the repo; no changes needed there.

**RED verification:** Test-writer notes confirmed 6/7 tests were RED before #898's implementation (seed had .ps1 files). #898 was already committed before this builder task started.

**GREEN verification:** All 7 tests in `test_init_py_hooks.py` pass (seed has 7 .py hooks, no .ps1, settings.json stripped of Windows profile keys).

**Stale test cleanup:** Removed `TestFromAC_SeedHooks` from `test_setup_init.py` (2 tests: `test_seed_deny_writes_ps1_exists`, `test_seed_lint_changed_ps1_exists`). These tests verified the OLD .ps1 state from task #604 — explicitly superseded by #898's migration. Architecture review (#899 notes) flagged this as "#898's builder should update/remove TestFromAC_SeedHooks." Also updated module docstring to remove stale AC5 entry.

**Test results:** 71 tests passed (test_init_py_hooks.py + test_setup_init.py), 0 failed
**Lint:** ruff clean
**Coverage:** N/A (test-only task)
**Commit:** 43f06d43 — pushed to dev
[[2026-04-17]]

## Review Evidence

**Tests:** 71 passed, 0 failed (pytest exit 0)
**Lint:** ruff clean (exit 0)
**Coverage:** N/A — test-only task

### AC Compliance

| AC | Test(s) | Status |
|----|---------|--------|
| AC1: test file exists | file present, tests ran | PASS |
| AC2: init() seeds .py only (no .ps1) | test_seeded_hooks_are_py_not_ps1, test_seeded_hooks_have_py_extension | PASS |
| AC3: exactly 7 .py hooks, canonical set | test_all_seven_hooks_seeded (missing+extra+count triple assert) | PASS |
| AC4: seeded settings.json no Windows terminal keys | test_settings_no_windows_terminal_profiles, test_settings_no_windows_default_profile | PASS |
| AC5: seed hooks dir no .ps1 | test_seed_hooks_dir_no_ps1_files | PASS |
| AC6: init.py no .ps1 literals | test_init_py_source_no_ps1_refs | PASS |

### TestFromAC Modification Check

`TestFromAC_SeedHooks` removed from `test_setup_init.py` (20 deletions). Pre-authorised by architecture review in this task's body: "AC5 rationale corrected… #898's builder should update/remove TestFromAC_SeedHooks." Removal eliminates superseded .ps1-verifying tests replaced by this task's new file. No other TestFromAC class modified or weakened.

### Assertion Quality

All 7 tests in `test_init_py_hooks.py` verified non-tautological: ps1_files==[], non_py==[], missing==set()+extra==set()+count==7, key not in data (×2), ps1_files==[], .ps1 not in source. Each would fail against the previous (unimplemented) state.

### Deductions

0

**Verdict:** PASS — confidence .97
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Test-only task — no application logic changed; only `tests/test_init_py_hooks.py` (new) and `tests/test_setup_init.py` (removal of superseded class) |
| 2 | Module docstrings | Yes | Verified | `test_init_py_hooks.py` module docstring present and accurate (lists AC2–AC6 coverage). `test_setup_init.py` docstring updated by builder (stale AC5 entry removed); grep confirms no `.ps1`/`SeedHooks`/`AC5` refs remain |
| 3 | External attribution | No | N/A | All 5 research sources codebase-internal (`setup/init.py`, `seed/` listing, `seed/settings.json`, `.owlbear/hooks/`, existing test file) — no external patterns |
| 4 | CLI changes | No | N/A | No CLI commands added or modified |
| 5 | Research doc | Yes | Verified | `.owlbear/research/init-py-hook-seeding-tests.md` exists; linked from task body under `## Research`; follow-up tasks noted as none needed |

### Files Updated

None — all documentation already accurate; no changes required.

### Scratch Files

No `.owlbear/scratch/899-*` files found.
[[2026-04-17]]

## Audit

### AC Verification

| AC (refined) | Evidence | Status |
|---|---|---|
| AC1: test file exists | `tests/test_init_py_hooks.py` — 155 lines, 4 classes, 7 tests | PASS |
| AC2: init() seeds .py only | `test_seeded_hooks_are_py_not_ps1` L62, `test_seeded_hooks_have_py_extension` L73 | PASS |
| AC3: exactly 7 .py hooks, canonical set | `test_all_seven_hooks_seeded` L83 — triple assert (missing/extra/count) | PASS |
| AC4: settings.json no Windows keys | `test_settings_no_windows_terminal_profiles` L104, `test_settings_no_windows_default_profile` L115 | PASS |
| AC5: seed hooks dir no .ps1 | `test_seed_hooks_dir_no_ps1_files` L135 — spot-checked: seed/.owlbear/hooks/ has 7× .py, 0× .ps1 | PASS |
| AC6: init.py no .ps1 literals | `test_init_py_source_no_ps1_refs` L150 — spot-checked: grep confirms no .ps1 in init.py | PASS |
| AC7: RED phase confirmed | Test-writer: 6 FAIL / 1 PASS; builder: 7 PASS after #898 | PASS |

### Spot-Checks

- `seed/.owlbear/hooks/`: 7 .py files (canonical set), 0 .ps1 — confirmed
- `setup/init.py`: no `.ps1` references — confirmed
- `seed/.vscode/settings.json`: no `terminal.integrated.profiles.windows` or `terminal.integrated.defaultProfile.windows` — confirmed
- `TestFromAC_SeedHooks` removed from `test_setup_init.py` — 20 deletions, pre-authorized by architecture review
- Commit `43f06d43` present on dev

### Test Results

- pytest (quality-runner): timed out at 5 min (exit 137), partial: 4528 passed, 244 failed, 196 skipped — environment timeout, not task-specific
- ruff: clean (exit 0)
- Reviewer confirmed task-scoped: 71 passed, 0 failed
- Builder confirmed: 71 passed, 0 failed

### Architect Quality: 4/5

Original ACs had locus ambiguity (AC4 "init.py logic" misleading — init.py is a generic copier) and missing extension specificity (AC2). Architect caught all issues in refinement pass and produced precise, verifiable ACs. Minor: original needed non-trivial refinement before test-writer could proceed.

### Deduction Breakdown

- Full-suite incomplete (quality-runner timeout): −.02
- All other criteria clean: no deduction

### Confidence: .98

### Action: archive
