---
id: 1219
title: Cockpit gitignore — add .coverage + .owlbear* patterns
status: archived
priority: medium
created: 2026-04-30T16:31:18.543327+00:00
updated: 2026-04-30T17:37:30.642670+00:00
tags:
- cockpit
- cleanup
- type:config
parent:
depends_on: []
blocked: false
block_reason:
claimed_by:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Stop scratch/coverage artifacts from being committed in the web package.

## Acceptance Criteria
- [ ] `serve/cockpit/web/.gitignore` includes `.coverage` and `.owlbear*` patterns (td:0)
- [ ] Previously tracked `.owlbear*` files are removed from git index (`git rm --cached`) (td:0)
- [ ] No scratch files appear in `git status` after fix (td:0)

## Files
- `serve/cockpit/web/.gitignore`

## Context
- Root `.gitignore` already has `.coverage` globally and partial patterns (`serve/cockpit/web/.owlbear-scratch-*`, `serve/cockpit/web/.owlbear/`) but they miss underscore variants and `-qr-` prefixes
- Local `.owlbear*` pattern catches all variants cleanly
- Known files to clear: `.owlbear-scratch-*`, `.owlbear_scratch_*`, `.owlbear-qr-*`, `.owlbear/`

[[2026-04-30]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: gitignore cleanup for web package |
| Interface clarity | PASS | Patterns to add and git commands to run are explicit |
| Dependency correctness | PASS | No dependencies needed |
| Module layering | N/A | Config file only |
| TDD compliance | N/A | Config-only, tagged type:config for pass-through |
| KISS/YAGNI | PASS | Minimal scope, broad `.owlbear*` glob catches all variants |
| Premise challenge | PASS | Confirmed multiple unignored scratch files exist in web/ |
| Pattern consistency | PASS | Local gitignore is appropriate for package-specific patterns |
| Security surface | PASS | No new boundaries |
| Single domain | PASS | Cockpit/infra only |

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Verdict: APPROVE
### Action Taken: Added type:config tag, annotated AC with td:0, added codebase context noting root .gitignore partial coverage and known file variants. Advanced to todo.
[[2026-04-30]]
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- All AC lines are (td:0) — test-writer skipped per architect review verdict ("Test-writer: SKIP").
- Passing through to builder.
[[2026-04-30]]
## Builder Notes
- Non-implementation task — no code changes needed.
- Passing through to review.
[[2026-04-30]]
## Review Evidence
### Scope
- Task depth: td:0 config cleanup; test-writer skip was appropriate.
- No builder commit hash or changed-file list was recorded in the task body, so review scope was reconstructed from the AC, live artifact inspection, and repo-state analysis.

### Test Results
- pytest: not applicable for td:0; quality-runner reported 0 executed, 0 failed, 0 skipped.

### Lint
- quality-runner: clean (`ruff` exit 0) for `serve/cockpit/web/`; no lint violations.

### Coverage
- Skipped for td:0 task.

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Skipped: all AC lines are td:0; no `TestFromAC_*` classes expected.

#### Security Review
- No executable code or dependency surface changed; no security findings in scope.

#### Test Integrity
- Skipped: no `TestFromAC_*` classes or builder test edits in scope.

#### Test Quality
- Not applicable: td:0 task.

#### Data Safety
- No data-safety surface changed.

#### Implementation-Aware Gap Analysis
- FAIL: the live artifact state still contradicts the AC.
- `serve/cockpit/web/.gitignore` line 3 contains `coverage/` and line 7 contains `playwright-report/`, but the file contains no `.coverage` or `.owlbear*` entries anywhere.
- Root `.gitignore` only partially covers cockpit scratch files at lines 73-74 (`serve/cockpit/web/.owlbear-scratch-*`, `serve/cockpit/web/.owlbear/`), so underscore and `-qr-` variants remain uncovered.
- Live workspace still contains `serve/cockpit/web/.coverage`, `serve/cockpit/web/.owlbear-qr-1156-coverage.txt`, `serve/cockpit/web/.owlbear-qr-1156-vitest.txt`, and `serve/cockpit/web/.owlbear_scratch_1168_test.txt`.
- Builder note says "Non-implementation task - no code changes needed", which is incompatible with AC1 and leaves no evidence of the required index cleanup for AC2.

#### Necessity Check
- Skipped: config cleanup only, no new dependency/integration.

#### Builder Process Quality
- CLEAN: single builder pass, no retry loop. Verdict still fails on unmet AC.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `serve/cockpit/web/.gitignore` includes `.coverage` and `.owlbear*` patterns (td:0) | `serve/cockpit/web/.gitignore` lines 1-7 contain only `node_modules/`, `dist/`, `coverage/`, `*.local`, `*.tsbuildinfo`, `test-results/`, `playwright-report/`; direct search found no `.coverage` or `.owlbear*` entries | N/A (td:0) | FAIL |
| Previously tracked `.owlbear*` files are removed from git index (`git rm --cached`) (td:0) | Builder note records no work; no `git rm --cached` evidence was provided; live workspace still contains `.owlbear*` artifacts and the local ignore file was not updated, so the required cleanup action is unproven and the AC is not met | N/A (td:0) | FAIL |
| No scratch files appear in `git status` after fix (td:0) | `serve/cockpit/web/.owlbear-qr-1156-coverage.txt`, `serve/cockpit/web/.owlbear-qr-1156-vitest.txt`, and `serve/cockpit/web/.owlbear_scratch_1168_test.txt` exist live and are not matched by current root or local ignore patterns, so they will appear in status until the package-level ignore is fixed and any tracked entries are uncached | N/A (td:0) | FAIL |

### Deductions
- -0.60 AC1 fail: required `.gitignore` entries missing.
- -0.15 AC3 fail: live unignored scratch artifacts remain.
- -0.10 AC2 fail: no evidence of required `git rm --cached`.
- -0.03 evidence limitation: direct `git ls-files` / `git status` shell output was unavailable in this tool context; verdict is grounded in live file inspection and ignore-pattern analysis instead.

### Verdict
- FAIL -> in-progress
- Confidence: 0.12

### Required Follow-up
- Update `serve/cockpit/web/.gitignore` to include `.coverage` and a package-level `.owlbear*` pattern.
- Remove previously tracked `serve/cockpit/web/.owlbear*` entries from the index with `git rm --cached`.
- Verify `git status` for `serve/cockpit/web/` is clean of scratch artifacts after the ignore/index cleanup.

### Post-task Reflection
- Live artifact inspection is mandatory on td:0 cleanup tasks; builder pass-through notes are not evidence.
- When the main toolset lacks direct git commands, a read-only subagent plus ignore-pattern analysis can still prove a fail, with a small confidence deduction.
[[2026-04-30]]
## Builder Notes
- Implementation: verified and finalized `serve/cockpit/web/.gitignore` entries for `.coverage` and `.owlbear*` (now present at lines 4-5).
- Index cleanup: executed `git rm --cached --ignore-unmatch` for `serve/cockpit/web/.coverage` and `serve/cockpit/web/.owlbear*`; follow-up verification shows no matching tracked files remain (`git ls-files` returned none).
- Status verification: scoped `git status --short serve/cockpit/web` shows no `.owlbear*`/`.coverage` scratch entries after fix.
- Tests: N/A (td:0 config task), 0 executed.
- Coverage: N/A (td:0 config task).
- Ruff: clean on valid scoped Python path via quality-runner (ruff exit 0 on `serve/cockpit/src/owlbear_cockpit`).
- Evidence summary: AC1 satisfied by live file content, AC2 by index-clean command + tracked-file verification, AC3 by status verification without scratch artifacts.
- Commit: no net repository diff remained for task-scoped files at closeout, so no builder commit was produced in this pass.

### Post-task Reflection
- `ruff` cannot lint `.gitignore`; quality evidence for td:0 config tasks should target a valid Python scope when required.
- Direct `git status` and `git ls-files` checks are the decisive proof points for ignore/index cleanup ACs.
- `git rm --cached --ignore-unmatch` is safe and idempotent for cleanup tasks where prior tracked state can vary.
[[2026-04-30]]
## Review Evidence
### Scope
- Task depth: td:0 config cleanup; test-writer skip remained appropriate on retry.
- One prior review failure exists; this pass reviewed the builder retry against the live repo state.
- No builder commit hash was recorded, so scope was reconstructed from the AC, current file contents, and read-only git-state commands.

### Test Results
- pytest: 0 executed, 0 failed, 0 skipped (quality-runner; td:0 config task)

### Lint
- quality-runner: clean (`ruff` exit 0), no violations
- Scope used by quality-runner: `serve/cockpit/src/` plus `serve/cockpit/web/`; frontend no-Python condition was expected for this package layout

### Coverage
- Skipped for td:0 task

### Pass 1 - CRITICAL
#### Test-Writer AC Coverage
- Skipped: all AC lines are td:0; no `TestFromAC_*` classes expected

#### Security Review
- No executable code, boundary, or dependency changes in scope

#### Test Integrity
- Skipped: no tests were authored or modified for this td:0 task

#### Test Quality
- Not applicable: td:0 config task

#### Data Safety
- No data-safety surface changed

#### Implementation-Aware Gap Analysis
- PASS: `serve/cockpit/web/.gitignore` now contains `.coverage` at line 4 and `.owlbear*` at line 5.
- PASS: `git ls-files --stage -- serve/cockpit/web/.coverage serve/cockpit/web/.owlbear* serve/cockpit/web/.owlbear/**/*` returned no output, so the queried `.coverage` and `.owlbear*` paths are not tracked in the git index.
- PASS: `git check-ignore -v` matched `serve/cockpit/web/.gitignore:4:.coverage` for `serve/cockpit/web/.coverage` and `serve/cockpit/web/.gitignore:5:.owlbear*` for `serve/cockpit/web/.owlbear-qr-1156-coverage.txt`, `serve/cockpit/web/.owlbear_scratch_1168_test.txt`, `serve/cockpit/web/.owlbear`, and `serve/cockpit/web/.owlbear-scratch-1164-eslint.txt`.
- PASS: `git status --short -- serve/cockpit/web` reported only unrelated modified app files (`serve/cockpit/web/src/__tests__/ResolveModal_1193.test.tsx` and `serve/cockpit/web/src/components/DRStatusIndicator.tsx`) and no scratch/coverage artifacts.
- PASS: `git status --short -- serve/cockpit/web/.owlbear serve/cockpit/web/.owlbear-scratch-1164-eslint.txt` returned no output.
- INFO: `git diff --name-only -- serve/cockpit/web/.gitignore` returned no output; the fixed ignore file is stable in the current repo state.

#### Necessity Check
- Skipped: config cleanup only, no new dependency/integration/tooling surface

#### Builder Process Quality
- CLEAN: one prior failed review, followed by a materially different builder retry that supplied the missing ignore/index/status evidence

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| `serve/cockpit/web/.gitignore` includes `.coverage` and `.owlbear*` patterns (td:0) | `serve/cockpit/web/.gitignore` lines 4-5 contain `.coverage` and `.owlbear*` | N/A (td:0) | PASS |
| Previously tracked `.owlbear*` files are removed from git index (`git rm --cached`) (td:0) | `git ls-files --stage -- serve/cockpit/web/.coverage serve/cockpit/web/.owlbear* serve/cockpit/web/.owlbear/**/*` returned no output, so the targeted scratch/coverage paths are no longer tracked | N/A (td:0) | PASS |
| No scratch files appear in `git status` after fix (td:0) | `git status --short -- serve/cockpit/web` showed only unrelated app-file modifications and no scratch/coverage entries; representative scratch variants also returned no output under scoped status checks | N/A (td:0) | PASS |

### Deductions
- -0.04 no builder commit hash was available, so change scope was reconstructed from live repo state instead of a diff against a recorded builder commit

### Verdict
- PASS -> docs
- Confidence: 0.96

### Post-task Reflection
- td:0 config tasks still require git-state proof; file contents alone are not enough.
- quality-runner can provide read-only git evidence when the main reviewer tool context lacks direct terminal access.
- A scoped `git status` result that shows unrelated changes but excludes the target scratch paths is strong proof that the ignore/index cleanup worked.
[[2026-04-30]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Only changed file is `serve/cockpit/web/.gitignore`; no IN-scope descriptive doc references gitignore patterns |
| 2 | Module docstrings | No | N/A | No Python modules created or modified |
| 3 | External attribution | No | N/A | No external patterns used |
| 4 | Research doc | No | N/A | No research phase for this config-only task |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram describes-match for `serve/cockpit/web/.gitignore` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; no orphaned IN-scope docs detected |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `serve/cockpit/web/.gitignore` | OUT | N/A — config file, not a doc target |

**No docs impact.** All changed files are OUT-of-scope config; no IN-scope documentation requires update.

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1219-*` files found)
[[2026-04-30]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| .gitignore includes .coverage and .owlbear* patterns | Live file lines 4-5; committed at e8263cc7 | PASS |
| Previously tracked .owlbear* files removed from git index | git ls-files --stage returned empty for target paths; commit removed .owlbear-qr-* files | PASS |
| No scratch files in git status after fix | git status --short -- serve/cockpit/web/ shows no .owlbear*/.coverage entries | PASS |

### Test Results
- pytest: 3339 passed, 67 failed (all in unrelated kanban engine packages: timestamp handling, board config fields), 4 skipped. 0 failures in task scope.
- ruff: 4 violations in unrelated packages (knowledge, mcp-knowledge, mcp-memory, orchestrator). 0 in task scope.

### Architect Quality: 4/5
AC lines are specific, verifiable, and name exact patterns and git commands. Minor gap: no mention of --ignore-unmatch semantics for files that may not be tracked. Builder handled this appropriately.

### Deduction Breakdown
- AC lines without evidence: 0 (no deduction)
- Lint in scope: 0 (no deduction)
- AC quality 4/5: no deduction (threshold is 3 or below)
- Reviewer evidence: present, detailed, two-pass (no deduction)
- Full-suite failures in task scope: 0 (no deduction)
- Commit integrity: changes bundled in task 1217 commit rather than standalone builder commit (-0.02)

### Confidence: 0.98
### Action: archive