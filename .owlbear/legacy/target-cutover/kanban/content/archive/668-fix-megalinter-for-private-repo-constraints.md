---
id: 668
title: Fix megalinter for private repo constraints
status: archived
priority: medium
created: 2026-04-06T22:22:31.9554503+02:00
updated: 2026-04-07T11:47:49.3239216+02:00
started: 2026-04-07T11:47:49.3239216+02:00
completed: 2026-04-07T11:47:49.3239216+02:00
tags:
    - scope:ci
    - type:fix
    - type:config
parent: 672
class: standard
---

## Objective\nFix megalinter.yml for private repo constraints: SARIF upload requires GHAS (not available), APPLY_FIXES has no write permissions to commit.\n\n## Context\nmaba-pag/owlbear is a private repo. `github/codeql-action/upload-sarif` requires GitHub Advanced Security or a public repo. The SARIF step will error. Additionally, `.mega-linter.yml` configures `APPLY_FIXES` for ruff-format + markdownlint, but the job only has `contents: read` permissions, so fixes are silently lost.\n\n## Acceptance Criteria\n- [ ] SARIF upload step removed (private repo without GHAS)\n- [ ] APPLY_FIXES removed from .mega-linter.yml (no write permissions to commit fixes)\n- [ ] Upload-artifact step for reports preserved (primary output mechanism)\n- [ ] Job summary step still reports pass/fail\n- [ ] `security-events: write` permission removed (no longer needed without SARIF)\n- [ ] Job summary SARIF reference removed (lines 62-64 claim "SARIF results uploaded to Security tab" which is false after upload step removal)\n\n## Files Affected\n- .github/workflows/megalinter.yml\n- .mega-linter.yml

[[2026-04-07]] Tue 09:13
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | All changes address one concern: fixing megalinter for private-repo constraints |
| Interface clarity | PASS | AC specifies exact steps/lines to remove and preserve |
| Dependency correctness | PASS | No dependencies; standalone fix within epic #672 |
| Module layering | N/A | CI config files, no Python module layering |
| TDD compliance | N/A | YAML-only changes, no testable Python code. Tagged type:config for pass-through |
| KISS/YAGNI | PASS | Pure removals of broken features, minimal scope |
| Premise challenge | PASS | SARIF upload genuinely fails on private repos without GHAS; APPLY_FIXES with read-only perms silently loses fixes |
| Pattern consistency | PASS | Follows standard GitHub Actions workflow patterns |
| Security surface | PASS | Removing security-events:write permission reduces attack surface |
| Single domain | PASS | All CI infrastructure, single domain |

### AC Refinement
Added AC #6: Job summary SARIF reference removed (lines 62-64 of megalinter.yml say "SARIF results uploaded to Security tab" which is false after upload step removal). SARIF_REPORTER: true is intentionally kept so the SARIF file remains available in the artifact download.

### Builder Hints
- MARKDOWN_MARKDOWNLINT_ARGUMENTS contains --fix which is dead weight without APPLY_FIXES. Consider removing it (optional, not AC-required).
- SARIF_REPORTER: true should stay: the SARIF file in the artifact is still useful for local analysis.
- Added type:config pass-through tag (no testable Python code).

### Challenge Results
- Challenger: reconsider (confidence 0.85)
- Concern: Job summary SARIF reference (lines 62-64) would display false information after SARIF upload removal
- Architect response: accepted, added AC #6 to address the gap

### Verdict: APPROVE (via REFINE)
### Action Taken: Refined AC with missing job summary SARIF cleanup item, added type:config pass-through tag, approved to todo

[[2026-04-07]] Tue 09:17
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- AC references only YAML CI config files (.github/workflows/megalinter.yml, .mega-linter.yml). No Python interfaces exist.
- AC keywords scanned: no `implement`, `function`, `class`, `src/`, `.py`, `endpoint`, or `API` references found.
- Passing through to builder.

[[2026-04-07]] Tue 11:15
## Builder Notes

### Files Changed
- `.github/workflows/megalinter.yml` — removed `security-events: write` permission, removed "Upload SARIF report" step (codeql-action/upload-sarif), removed SARIF false-claim lines from job summary (`if [ -f ... ]` block)
- `.mega-linter.yml` — removed `APPLY_FIXES` block (PYTHON_RUFF_FORMAT + MARKDOWN_MARKDOWNLINT)

### AC Verification
- [x] SARIF upload step removed
- [x] APPLY_FIXES removed from .mega-linter.yml
- [x] Upload-artifact step for reports preserved
- [x] Job summary step still reports pass/fail
- [x] `security-events: write` permission removed
- [x] Job summary SARIF reference removed

### Test Results
- Non-implementation task (type:config) — no Python tests applicable. Pass-through confirmed.
- No ruff/pytest run needed (YAML-only changes).

### Lint Status
N/A — YAML config files only.

### Coverage
N/A

[[2026-04-07]] Tue 11:22
## Review Evidence

### Task Type
`type:config` pass-through — YAML-only changes, no Python code. No tests applicable (confirmed by architect + test-writer).

### Tests
N/A — type:config pass-through. No `TestFromAC_*` files created or modified.

### Lint
N/A — no Python source files changed.

### Coverage
N/A

### Changed Files Verified
- `.github/workflows/megalinter.yml` — read in full
- `.mega-linter.yml` — read in full

### AC Compliance Table

| AC | Requirement | Evidence | Status |
|----|-------------|----------|--------|
| 1 | SARIF upload step removed | No `codeql-action/upload-sarif` step exists; 5 steps total (Checkout, MegaLinter, Upload artifact, Job summary, Fail if lint failed) | ✅ PASS |
| 2 | APPLY_FIXES removed from .mega-linter.yml | No `APPLY_FIXES` key present in .mega-linter.yml | ✅ PASS |
| 3 | Upload-artifact step preserved | Step present (line 36–44), `actions/upload-artifact@ea165...`, path: megalinter-reports, retention-days: 15 | ✅ PASS |
| 4 | Job summary step still reports pass/fail | Step present (lines 46–57), outcome-conditional pass/fail written to GITHUB_STEP_SUMMARY | ✅ PASS |
| 5 | `security-events: write` removed | Workflow: `contents: read` only. Job: `contents: read` + `statuses: write`. No `security-events` entry. | ✅ PASS |
| 6 | Job summary SARIF reference removed | Job summary contains only pass/fail messages — no SARIF or "Security tab" reference | ✅ PASS |

### Non-Blocking Observation
`MARKDOWN_MARKDOWNLINT_ARGUMENTS: "--fix"` remains in .mega-linter.yml — dead weight without APPLY_FIXES. Architect explicitly flagged as optional/not AC-required. No deduction.

### Security
Permissions reduced (no `security-events: write`). Minimal required perms only. `SARIF_REPORTER: true` intentionally retained per architect (SARIF artifact still useful for local analysis).

### Deductions
0

### Verdict
Confidence: .97 → PASS

[[2026-04-07]] Tue 11:30
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Behavior/API change | No | N/A | YAML-only CI config changes. `copilot-instructions.md` references `.mega-linter.yml` only in the branch file listing (line 12), not as behavioral documentation. No update needed. |
| 2 | Module docstrings | No | N/A | No Python files created or modified. |
| 3 | External attribution | No | N/A | Changes are pure removals of standard GitHub Actions steps; no new external patterns adopted. |
| 4 | CLI changes | No | N/A | No CLI commands added or modified. |
| 5 | Research doc | No | N/A | No research phase; no `.owlbear/research/` file produced for this task. |

### Files Updated
None — no documentation impact identified.

### Scratch Files Cleaned
None — no `.owlbear/scratch/668-*` files existed.

[[2026-04-07]] Tue 11:47
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| SARIF upload step removed | git diff: codeql-action/upload-sarif step deleted from megalinter.yml | PASS |
| APPLY_FIXES removed from .mega-linter.yml | git diff: APPLY_FIXES block (PYTHON_RUFF_FORMAT + MARKDOWN_MARKDOWNLINT) deleted | PASS |
| Upload-artifact step preserved | megalinter.yml lines 37-43: actions/upload-artifact present | PASS |
| Job summary step still reports pass/fail | megalinter.yml lines 45-56: conditional pass/fail messages present | PASS |
| security-events: write removed | megalinter.yml: only contents:read + statuses:write in job permissions | PASS |
| Job summary SARIF reference removed | git diff: if-block with "SARIF results uploaded to Security tab" deleted from job summary | PASS |

### Test Results
- pytest: 3481 passed, 424 failed, 18 skipped, 1 error (all pre-existing, unrelated to YAML-only changes)
- ruff: 5 errors in serve/mcp-kanban/ (pre-existing, unrelated to #668)

### Architect Quality: 5/5
AC was specific and complete. Each item named exact targets (steps, keys, permissions, line references). AC #6 added via challenger feedback, demonstrating good upstream rigor.

### Deduction Breakdown
- No deductions. All 6 AC lines verified with diff evidence. Reviewer section present and detailed (.97 PASS). Pre-existing test/lint issues are outside task scope.

### Confidence: .98
### Action: archive

## Commits
| Commit | Type | Files | Tasks |
|--------|------|-------|-------|
| dc76181 | fix | .github/workflows/megalinter.yml, .mega-linter.yml | #668 |
| 0810728 | chore | kanban board files | #668 |

### Note
Builder did not commit deliverables (changes were unstaged). Committed as audit leftover. Non-blocking for this task but noted for process improvement.
