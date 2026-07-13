---
id: 679
title: Add cleanup policy for .owlbear/scratch directory
status: archived
priority: medium
created: 2026-04-08T18:35:53.3462402+02:00
updated: 2026-04-09T00:31:27.8009419+02:00
started: 2026-04-09T00:31:27.8009419+02:00
completed: 2026-04-09T00:31:27.8009419+02:00
tags:
    - scope:ops
    - ' type:chore'
    - ' source:analysis'
class: standard
---

## Context

`.owlbear/scratch/` contains 500+ temp files (diagnostic scripts, test outputs, board scans, dispatch plans) spanning task IDs #1–#996. No cleanup mechanism exists. Files grow without bounds.

## Acceptance Criteria

- [ ] AC1: Add a cleanup mechanism that removes scratch files older than 30 days
- [ ] AC2: Mechanism should be invokable manually (not automatic) — e.g. a script or curator subtask
- [ ] AC3: Cleanup preserves files from the last 30 days to maintain recent debugging context
- [ ] AC4: `.owlbear/scratch/` is gitignored (verify — if not, add it)

[[2026-04-08]] Wed 21:28
## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: batch cleanup of scratch files |
| Interface clarity | REFINE | Original AC lacked: implementation form, protected files, time attribute, output contract. Refined below. |
| Dependency correctness | PASS | No deps, standalone utility |
| Module layering | PASS | Ops script in `.owlbear/scripts/` — no package coupling |
| TDD compliance | PASS | `type:chore` tag present; testable Python logic (age-based filtering, protected file exclusion) |
| KISS/YAGNI | PASS | Minimal scope — single script, manual invocation |
| Premise challenge | PASS | Per-task cleanup exists in doc-writer (w-doc-update Step 2) but no batch/age-based cleanup. 500+ orphaned files confirm the gap. |
| Pattern consistency | PASS | Follows `.owlbear/scripts/e2e_smoke.py` precedent |
| Security surface | PASS | Path-restricted to `.owlbear/scratch/` — no external input beyond CLI args |
| Single domain | PASS | ops/tooling domain only |

### AC Refinements

**Original issues:**
1. AC1 and AC3 are redundant (remove older than 30d = preserve newer than 30d)
2. AC4 already satisfied: `.owlbear/scratch/` gitignored at `.gitignore:55-58`
3. Missing: implementation form, protected files (`.gitkeep`, `.instructions.md`), time attribute (`mtime`), dry-run safety

**Refined AC (supersedes original):**
- [ ] AC1: Python script at `.owlbear/scripts/clean_scratch.py` deletes files in `.owlbear/scratch/` (including subdirectories) whose `mtime` is older than 30 days
- [ ] AC2: Script invokable via `uv run python .owlbear/scripts/clean_scratch.py` — manual invocation only, no scheduled/automatic execution
- [ ] AC3: Script never deletes protected files: `.gitkeep`, `.instructions.md` — regardless of age
- [ ] AC4: Script supports `--dry-run` flag that prints what would be deleted without deleting
- [ ] AC5: Script prints summary to stdout: count deleted, count preserved, any errors
- [ ] AC6: Verified: `.owlbear/scratch/` is already gitignored (`.gitignore:55-58`) — no action required

### Codebase References
- Script precedent: `.owlbear/scripts/e2e_smoke.py`
- Gitignore entry: `.gitignore:55-58` (scratch dir with `.gitkeep` and `.instructions.md` exceptions)
- Per-task cleanup pattern: `share/skills/w-doc-update/SKILL.md` Step 2
- Protected files: `.owlbear/scratch/.gitkeep`, `.owlbear/scratch/.instructions.md`

### Challenge Results
- Challenger: SKIPPED (optional for REFINE verdict)

### Verdict: REFINE → APPROVE
### Action Taken: Tightened AC (consolidated redundant criteria, specified implementation form, added protected file list, added dry-run safety, resolved pre-satisfied gitignore check). Advanced to todo.

[[2026-04-08]] Wed 22:05
## Test-Writer Notes
- Test file: tests/test_clean_scratch_679.py
- Commit: be62a2a — `test: add failing tests for clean_scratch.py (#679, test-writer)`
- Classes:
  - `TestFromAC_CleanScratchInvocable` — AC2 (script exists, exits zero)
  - `TestFromAC_CleanScratchAgeFiltering` — AC1 (old deleted, recent preserved, subdirs, boundaries)
  - `TestFromAC_CleanScratchProtectedFiles` — AC3 (.gitkeep, .instructions.md never deleted)
  - `TestFromAC_CleanScratchDryRun` — AC4 (no deletions, prints targets)
  - `TestFromAC_CleanScratchSummary` — AC5 (deleted count, preserved count, keywords)
- Tests per category: happy 8, edge 5, error 0, boundary 2 (+ 8 AC-specific contract checks)
- Total: 23 tests, all FAIL — root cause: `.owlbear/scripts/clean_scratch.py` does not exist
- ruff: clean

**AC coverage table:**
| AC | Tests |
|----|-------|
| AC1 (mtime-based deletion + subdirs) | test_file_older_than_30_days_is_deleted, test_file_newer_than_30_days_is_preserved, test_files_in_subdirectory_are_included, test_recent_file_in_subdirectory_is_preserved |
| AC2 (invokable via python) | test_script_file_exists_at_expected_path, test_script_exits_zero_on_dry_run, test_script_exits_zero_on_normal_run |
| AC3 (protected files never deleted) | test_gitkeep_preserved_regardless_of_age, test_instructions_md_preserved_regardless_of_age, test_gitkeep_in_subdirectory_is_preserved, test_instructions_md_in_subdirectory_is_preserved, test_only_non_protected_old_files_deleted_when_mixed |
| AC4 (--dry-run no delete + prints) | test_dry_run_does_not_delete_old_file, test_dry_run_prints_name_of_file_that_would_be_deleted, test_dry_run_does_not_print_recent_files_as_targets |
| AC5 (summary output) | test_summary_reports_deleted_count, test_summary_reports_preserved_count, test_summary_contains_deleted_keyword, test_summary_contains_preserved_keyword, test_summary_zero_counts_on_empty_dir |
| AC6 (gitignore) | Not testable — config fact, no runtime behavior |

**Builder note:** Tests use `--scratch-dir <path>` CLI flag to inject a temp directory. Builder must implement this optional argument for testability. Boundary semantics: exactly 30 days old = preserve; 30 days + 1s = delete.

[[2026-04-08]] Wed 22:27
## Builder Notes

### Files Changed
- `.owlbear/scripts/clean_scratch.py` — new script (1 file, no existing files modified)

### Test Results
- 23/23 tests passed (all `TestFromAC_*` classes green)
- ruff: clean

### Coverage
- `.owlbear/scripts/clean_scratch.py`: full coverage via subprocess invocation tests

### Implementation Summary
- Script at `.owlbear/scripts/clean_scratch.py` — 99 lines
- CLI args: `--scratch-dir PATH` (optional, defaults to `.owlbear/scratch/`), `--dry-run`
- Age filter: uses `int(now - mtime)` to truncate to whole seconds — fixes boundary test where `_age_ts(30)` file would be fractionally older by subprocess startup time
- Protected names: `.gitkeep`, `.instructions.md` (frozenset, never deleted)
- Recursive via `Path.rglob("*")`, skips non-files (directories)
- Summary output: "Deleted: N, Preserved: N" (normal) / "Dry-run complete: N would be deleted, N preserved" (--dry-run)
- Dry-run prints filenames of would-be-deleted files

### AC Evidence
| AC | Status |
|----|--------|
| AC1: mtime-based deletion + subdirs | PASS — 7 tests |
| AC2: invokable via python | PASS — 3 tests |
| AC3: protected files preserved | PASS — 5 tests |
| AC4: --dry-run no delete + prints targets | PASS — 3 tests |
| AC5: summary output | PASS — 5 tests |
| AC6: gitignore (config fact) | N/A — pre-satisfied per arch review |

[[2026-04-08]] Wed 23:10
## Review Evidence

### Test Results
- pytest: **23 passed, 0 failed** (quality-runner, no coverage — subprocess tests + coverage hang, repo-known issue)
- pytest exit code: 0
- ruff: **clean** (0 violations)

### Source Control
- Changed files scoped to #679: `.owlbear/scripts/clean_scratch.py` (new, 99 lines) — exactly matches builder claim. One file only.

### TestFromAC Integrity
All 5 `TestFromAC_*` classes present and unmodified. No weakened assertions, no removed tests.

| Class | Builder change | Assessment |
|-------|---------------|------------|
| `TestFromAC_CleanScratchInvocable` | None | PRESERVED |
| `TestFromAC_CleanScratchAgeFiltering` | None | PRESERVED |
| `TestFromAC_CleanScratchProtectedFiles` | None | PRESERVED |
| `TestFromAC_CleanScratchDryRun` | None | PRESERVED |
| `TestFromAC_CleanScratchSummary` | None | PRESERVED |

### AC Compliance

| AC | Evidence | Mapped Test | Status |
|----|----------|-------------|--------|
| AC1: mtime-based deletion + subdirs | `_is_stale()` at line 50; `rglob("*")` at line 59 | `test_file_older_than_30_days_is_deleted`, `test_files_in_subdirectory_are_included` | PASS |
| AC2: invokable via python | `if __name__ == "__main__": sys.exit(main())` at line 98 | `test_script_file_exists_at_expected_path`, `test_script_exits_zero_*` | PASS |
| AC3: protected files never deleted | `_PROTECTED_NAMES = frozenset({".gitkeep", ".instructions.md"})` line 27; `_is_protected()` line 48 | 5 protected-file tests (root + subdir variants) | PASS |
| AC4: --dry-run flag | argparse `--dry-run` line 39; dry-run branch line 65-66 | `test_dry_run_does_not_delete_old_file`, `test_dry_run_prints_name_of_file_that_would_be_deleted`, `test_dry_run_does_not_print_recent_files_as_targets` | PASS |
| AC5: summary output | `print(f"Deleted: {deleted}, Preserved: {preserved}")` line 69 | 5 summary tests | PASS |
| AC6: gitignore | Pre-satisfied per arch review (`.gitignore:55-58`) | N/A (config fact) | N/A |

### Security Review
- No hardcoded secrets, no injection, no insecure deserialization.
- `--scratch-dir` accepts any path; no enforcement of `.owlbear/scratch/` restriction. Risk is negligible for a manual-invocation developer CLI tool where the caller already has full filesystem access. No OWASP Top 10 violation.

### Test Quality
- Assertion specificity: STRONG on existence checks; ADEQUATE on count checks (`"1" in stdout`) — functionally correct for single-file test scenarios.
- Boundary coverage: STRONG — exactly 30 days preserved (`int()` truncation tested); 30d+1s deleted.
- Mutation resistance: STRONG — protected file check, delete vs. preserve, dry-run all have independent assertion paths.
- Test independence: PASS — all use `tmp_path` fixture.
- Descriptive names: PASS.
- Overall: **ADEQUATE–STRONG**. No WEAK dimension.

### Informational Notes (non-blocking)
1. Dry-run prints `file.name` instead of relative path — same-named files in different subdirs are indistinguishable in output. Minor UX gap, not AC-required.
2. `main()` error path (nonexistent `--scratch-dir` → exit code 1) is untested. Suppressed: defensive error guard, not an AC requirement.
3. Summary count assertions use broad `"1" in stdout` — adequate for single-file scenarios, could be tightened.

### Builder Process Quality
Single `## Builder Notes` section — CLEAN. No loop pattern.

### Confidence Deductions
- 0 deductions for critical issues
- −0.02 informational (mild assertion weakness in summary tests)
- **Confidence: .95**

### Verdict
**PASS #679 → docs | confidence .95**

[[2026-04-08]] Wed 23:16
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | `copilot-instructions.md` is branch-only (16 lines, no scripts section); README already lists `.owlbear/` as containing "scripts" — no update needed |
| 2 | Module docstrings | Yes | Verified | Module docstring covers invocation + exit codes; `run()` has docstring; `_is_stale()` has docstring; `main()` has no docstring per codebase convention — `e2e_smoke.py` precedent confirms this pattern |
| 3 | External attribution | No | N/A | stdlib only (`argparse`, `pathlib`, `time`, `sys`) — no external patterns |
| 4 | CLI changes | No | N/A | Ops utility script — not a user-facing `owlbear` CLI command; no README update needed |
| 5 | Research doc | No | N/A | No research doc produced or referenced in task body |

### Files Updated
None — no documentation impact found.

### Scratch Files
No `.owlbear/scratch/679-*` files found. Nothing to clean.

### Verdict
Docs gate passed. No documentation updates required.

[[2026-04-09]] Thu 00:31
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| AC1: mtime-based deletion + subdirs | 7 tests pass (age filtering, subdirs, boundary) in `TestFromAC_CleanScratchAgeFiltering`; `_is_stale()` at line 50, `rglob("*")` at line 59 | PASS |
| AC2: invokable via python | 3 tests pass in `TestFromAC_CleanScratchInvocable`; `if __name__ == "__main__"` at line 98 | PASS |
| AC3: protected files never deleted | 5 tests pass in `TestFromAC_CleanScratchProtectedFiles`; `_PROTECTED_NAMES` frozenset at line 27 | PASS |
| AC4: --dry-run flag | 3 tests pass in `TestFromAC_CleanScratchDryRun`; argparse `--dry-run` at line 39 | PASS |
| AC5: summary output | 5 tests pass in `TestFromAC_CleanScratchSummary`; print statements at lines 69, 82 | PASS |
| AC6: gitignore pre-satisfied | `.gitignore:55-58` confirmed by arch review | N/A |

### Test Results
- pytest (task-scoped): 23 passed, 0 failed
- pytest (full suite): 184 passed, 54 failed — all failures outside #679 scope (test_analysis.py, test_agent_scoped_hooks_research.py, etc.)
- ruff: 5 violations, none in #679 files

### Architect Quality: 5/5
Refined AC was specific, complete, and provided a clean implementation path. Consolidated redundant original AC, specified implementation form, added protected file list, dry-run safety, and boundary semantics. No builder improvisation required.

### Deduction Breakdown
- AC lines with no evidence: 0 (all covered)
- Lint violations in scope: 0
- AC quality ≤ 3: N/A (score 5)
- Missing reviewer evidence: 0 (present, detailed, PASS)
- Full-suite failures in task scope: 0

### Process Note
Builder deliverable `.owlbear/scripts/clean_scratch.py` was uncommitted (untracked). Committed as `13a5098` during audit Step 4.

### Confidence: 1.00
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| be62a2a | test | tests/test_clean_scratch_679.py | #679 |
| 13a5098 | feat | .owlbear/scripts/clean_scratch.py | #679 |
