---
id: 898
title: Update seed/ with .py hooks and clean settings
status: archived
priority: needed
created: 2026-04-16T22:54:12.457895+00:00
updated: 2026-04-17T09:30:24.119118+00:00
tags:
- phase-2
- scope:setup
- config
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

- [ ] All .ps1 files in seed/.owlbear/hooks/ replaced with .py equivalents (copies from .owlbear/hooks/)
- [ ] 7 .py hooks present in seed/.owlbear/hooks/ (fix drift: seed currently has 6, missing deny-scratch-only-writes)
- [ ] Windows-only terminal profiles removed from seed/.vscode/settings.json (no pwsh.exe paths)
- [ ] No .ps1 references remain in seed/
- [ ] grep -r ".ps1" seed/ returns no results
- [ ] grep -r "powershell" seed/ returns no results

## Files

- `seed/.owlbear/hooks/*.py` (new, replacing .ps1)
- `seed/.vscode/settings.json` (edit)
[[2026-04-17]]

## Research

- Research doc: .owlbear/research/seed-py-hooks-and-settings.md
- Sources: 5 studied, 4 high-relevance (all codebase)
- Recommendation: Proceed as T1 config task — copy 7 .py hooks, delete 6 .ps1, remove 3 Windows-only settings blocks (confidence: 0.92)
- Follow-up tasks created: none (task itself is the actionable item)
- Decision requests: none

Key findings:

1. All 7 .py hooks exist in .owlbear/hooks/ and are tested (12 test files). Ready to copy.
2. Seed drift confirmed: 6 hooks in seed vs 7 in dev (missing deny-scratch-only-writes).
3. settings.json has 3 removable blocks: [powershell] formatter, defaultProfile.windows, profiles.windows.
4. Dependencies #894–896 and parent #890 are absent from the board — stale references from incomplete decomposition. Actual prerequisites (hooks ported, tests written) are met.
[[2026-04-17]]

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: sync seed/ hooks to .py and clean Windows-only settings |
| Interface clarity | PASS | AC specifies exact file operations, counts, and grep verification commands |
| Dependency correctness | PASS (with caveat) | depends_on #894–896 and parent #890 are absent from board — stale refs from incomplete decomposition. Actual prerequisites met: 7 .py hooks exist in `.owlbear/hooks/`, 11 test files cover them. Stale deps need cleanup but don't block. |
| Module layering | N/A | Config-only task, no module imports |
| TDD compliance | PASS | Non-implementation config task; existing .py hooks already covered by 11 test files |
| KISS/YAGNI | PASS | Minimal scope: copy 7 files, delete 6, edit 1 settings block |
| Premise challenge | PASS | Seed drift is real (6 .ps1 vs 7 .py in dev). Windows-only settings confirmed at lines 18–20, 152, 154–158 of seed/.vscode/settings.json |
| Pattern consistency | PASS | Follows established pattern: `.owlbear/hooks/` is source of truth, seed/ mirrors it |
| Security surface | PASS | No new boundaries — file copy within repo |
| Single domain | PASS | scope:setup only |

### Failure Mode Map

N/A — config copy/delete task, no runtime codepaths.

### Challenge Results

- Challenger: FALLBACK — challenger agent not available in agent roster
- Architect response: N/A — trivial T1 config task, low risk, reversible changes

### Codebase Verification

- `.owlbear/hooks/` contains exactly 7 .py hooks: allow-stances-only, deny-code-writes, deny-scratch-only-writes, deny-src-writes, deny-writes, lint-changed, session-context
- `seed/.owlbear/hooks/` contains 6 .ps1 files (missing deny-scratch-only-writes) — drift confirmed
- `grep ".ps1" seed/` → 6 hits (all in seed/.owlbear/hooks/*.ps1)
- `grep "powershell" seed/` → 3 hits (seed/.vscode/settings.json lines 18–19, 156)
- `grep "pwsh" seed/` → 4 hits (seed/.vscode/settings.json lines 152, 155, 157)
- .py hooks contain no .ps1 references — clean copies

### Non-implementation Tagging

**ACTION NEEDED:** Task has `config` tag but needs `type:config` for test-writer pass-through. Add `type:config` tag before test-writer picks this up.

### Stale Metadata

depends_on references #894, #895, #896 and parent #890 are absent from the board. These should be cleared to avoid confusion, but do not block approval.

### Verdict: APPROVE

### Action Taken: Advanced to todo. Builder should: (1) copy 7 .py hooks from `.owlbear/hooks/` to `seed/.owlbear/hooks/`, (2) delete 6 .ps1 files from `seed/.owlbear/hooks/`, (3) remove Windows-only blocks from `seed/.vscode/settings.json` ([powershell] formatter, defaultProfile.windows, profiles.windows), (4) verify with grep

[[2026-04-17]]

## Test-Writer Notes

- Test file: tests/test_seed_py_hooks_and_clean_settings_898.py
- Classes: TestFromAC_SeedPyHooksPresent, TestFromAC_SeedPs1FilesRemoved, TestFromAC_SeedNoPs1References, TestFromAC_SeedNoPowershellReferences, TestFromAC_SeedSettingsWindowsProfilesRemoved
- Tests per category: happy 4 (py hooks present/named/nonempty), edge 3 (deny-scratch-only drift, profiles.windows key, pwsh key), error 7 (each ps1 absent + no ps1 files/strings), boundary 4 (no powershell strings, no pwsh.exe, no defaultProfile.windows)
- Total: 18 tests, all FAIL
- ruff: clean
- Commit: 3bdfc0c6

AC coverage:

| AC | Tests |
|----|-------|
| AC1: .ps1 replaced with .py equivalents | test_no_ps1_files_in_seed_hooks_dir, test_{each ps1}_absent (×6) |
| AC2: 7 .py hooks present, deny-scratch-only-writes drift fixed | test_exactly_seven_py_hooks_exist, test_all_expected_hook_names_present, test_deny_scratch_only_writes_py_exists, test_each_py_hook_is_nonempty |
| AC3: Windows-only terminal profiles removed from settings.json | test_no_default_profile_windows_key, test_no_pwsh_terminal_profile, test_no_pwsh_exe_path, test_no_profiles_windows_key |
| AC4/AC5: grep .ps1 seed/ → no results | test_no_ps1_files_anywhere_in_seed, test_no_ps1_string_in_seed_files |
| AC6: grep powershell seed/ → no results | test_no_powershell_string_in_seed_files |
[[2026-04-17]]

## Builder Notes

### Files Changed

- `seed/.owlbear/hooks/` — deleted 6 .ps1 files; added 7 .py hooks (copies from `.owlbear/hooks/`)
- `seed/.owlbear/hooks/session-context.py` — stripped `.ps1` back-reference comment from docstring (source copy retained)
- `seed/.vscode/settings.json` — removed 3 Windows-only blocks: `[powershell]` formatter, `terminal.integrated.defaultProfile.windows`, `terminal.integrated.profiles.windows`
- `pyproject.toml` — added `per-file-ignores` for `seed/.owlbear/hooks/*.py` (C901/INP001/T201, same as source hooks)

### Test Results

- RED verified: 18/18 FAILED before implementation
- GREEN: 18/18 PASSED after implementation
- No regressions

### Lint

- `uv run ruff check serve/ tests/ seed/` → All checks passed!

### Builder-Discovered Edge Case

`session-context.py` docstring contained `Python port of session-context.ps1 — bug-for-bug equivalent.` — this `.ps1` reference failed AC5. Stripped from seed copy only; source file in `.owlbear/hooks/` unchanged. No `TestBuilderDiscovered` class created (this is a config file edit, not a code logic discovery; the AC test itself covers it).

### Commit

`0910a443` — feat: update seed/ with .py hooks and clean Windows-only settings (#898)
[[2026-04-17]]

## Review Evidence

### Test Results

- pytest: 18 passed, 0 failed (quality-runner, independent run)

### Lint

- clean: true (ruff on tests/test_seed_py_hooks_and_clean_settings_898.py + seed/)

### Coverage

- N/A — config task, no production modules

### Pass 1 — CRITICAL

#### Test-Writer AC Coverage

| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| AC1: .ps1 → .py replacements | test_no_ps1_files_in_seed_hooks_dir + 6 per-file absence tests | Yes — explicit `not exists()` + rglob assertions | COVERED |
| AC2: 7 .py hooks, deny-scratch-only-writes drift fixed | test_exactly_seven_py_hooks_exist, test_all_expected_hook_names_present, test_deny_scratch_only_writes_py_exists, test_each_py_hook_is_nonempty | Yes — exact count (==7), exact name set, file.exists(), st_size > 0 | COVERED |
| AC3: Windows-only profiles removed from settings.json | test_no_default_profile_windows_key, test_no_pwsh_terminal_profile, test_no_pwsh_exe_path, test_no_profiles_windows_key | Yes — asserting substring absence in file text | COVERED |
| AC4/AC5: grep .ps1 seed/ → no results | test_no_ps1_files_anywhere_in_seed, test_no_ps1_string_in_seed_files | Yes — rglob *.ps1 + full text scan | COVERED |
| AC6: grep powershell seed/ → no results | test_no_powershell_string_in_seed_files | Yes — case-insensitive full text scan | COVERED |

#### Security Review

- No security issues. Config-only task (file copies, key deletions, lint suppression config). No new code paths, external inputs, or dependencies.

#### Test Integrity

- 18 tests present matching test-writer's declared 18. No TestFromAC_* modifications detected.

| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| All 18 TestFromAC_* tests | None — builder did not touch test file | PRESERVED |

#### Test Quality: STRONG

- Assertion specificity: exact counts, exact name sets, specific `.exists()` / `.stat().st_size` / substring checks. No lazy assertions.
- Negative-path coverage: all ps1-absent tests are explicit negative assertions.
- Mutation sensitivity: flipping any file operation would trigger multiple test failures.

#### Data Safety: N/A

#### Test Gap Analysis: CLEAN

- Builder edge case (session-context.py .ps1 comment stripped from seed copy) covered by `test_no_ps1_string_in_seed_files`.
- pyproject.toml per-file-ignores addition mirrors existing .owlbear/hooks/*.py pattern; implicitly validated by lint pass.

#### Builder Process: CLEAN (1 iteration)

### AC Compliance

All 6 AC lines: PASS

### Verdict

Confidence: .97 → PASS
[[2026-04-17]]

## Docs Gate

### Checklist

| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | Config-only task: seed/ file copies + settings.json deletions. No runtime behavior, no API, no convention change. copilot-instructions.md unchanged. |
| 2 | Module docstrings | No | N/A | No Python modules created/modified. seed/.owlbear/hooks/*.py are excluded scripts (per-file-ignores in pyproject.toml), not public-API modules. |
| 3 | External attribution | No | N/A | All sources internal codebase only (hooks, settings.json, brief). No external repos/articles. |
| 4 | CLI changes | No | N/A | No CLI additions or modifications. |
| 5 | Research doc | Yes | Verified | .owlbear/research/seed-py-hooks-and-settings.md exists and linked from task body. |

### Files Updated

- None

### Scratch Files Cleaned

- None (no .owlbear/scratch/898-* files found)
[[2026-04-17]]

## Audit (Incomplete — Blocked)

### Deliverable Verification: PASS

All deliverables confirmed present via Explore subagent:

- 7 .py hooks in seed/.owlbear/hooks/ (exact expected names, no .ps1 files)
- No .ps1 or powershell references in seed/
- Windows-only terminal settings removed from seed/.vscode/settings.json
- Test file: 18 tests across 5 classes
- Research doc exists
- Commit 0910a443 exists

### Reviewer Evidence: Present, Detailed, PASS (.97)

Code-level findings trusted — reviewer mapped all 6 AC lines with specific test assertions.

### Blocking Issue

Quality-Runner subagent dispatch failed (returned async stub, no results file produced). Per w-task-verification fallback protocol: auditor has no execution tools and must block rather than improvise test execution.

### Partial Assessment (pre-block)

- AC spot-check: 2/6 AC lines independently verified via Explore (file listing, grep). Both PASS.
- Reviewer section: present, detailed, .97 confidence — trusted.
- AC quality: ~4/5 (specific, complete, minor gap around pyproject.toml change not in AC but handled).
- Cannot compute final confidence without full suite results.
[[2026-04-17]]

## Audit Completion (Manual)

Quality-Runner block resolved: full test suite verified independently (4318 pass, 222 RED-phase, 0 regressions, no hangs). All 18 task-specific tests pass. Unblocking to release downstream tasks #900, #901, #904, #905.
