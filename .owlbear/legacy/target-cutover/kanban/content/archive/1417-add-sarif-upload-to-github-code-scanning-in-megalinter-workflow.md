---
id: 1417
title: Add SARIF upload to GitHub Code Scanning in MegaLinter workflow
status: archived
priority: medium
created: 2026-05-07T23:28:57.957311+00:00
updated: 2026-05-08T15:40:02.989357+00:00
tags:
- scope:infra
- type:config
parent: 1413
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Add SARIF upload step (`github/codeql-action/upload-sarif`) after MegaLinter produces SARIF reports. This publishes findings to the GitHub Security tab for baseline tracking. See `.owlbear/research/1413-ci-sast-baseline.md` gap G2.

## Acceptance Criteria
P1: `github/codeql-action/upload-sarif` step added to `.github/workflows/megalinter.yml`, SHA-pinned per workflow convention (td:0)
P1: Step uses `sarif_file: megalinter-reports/megalinter-report.sarif` and `category: megalinter` (td:0)
P2: Step uses `if: always()` condition (td:0)
P2: Step uses `continue-on-error: true` to handle missing GHAS gracefully (td:0)
P2: Job permissions include `security-events: write` and `actions: read` (td:0)
P2: Step placed after "Upload MegaLinter reports" artifact step, before "Fail if lint failed" gate (td:0)

## Research
- Research doc: .owlbear/research/1417-sarif-upload-code-scanning.md
- Sources: 6 studied, 4 high-relevance (MegaLinter SARIF Reporter docs, GitHub SARIF upload docs, codeql-action upload-sarif action.yml, oxsecurity/megalinter source)
- Recommendation: Add single `github/codeql-action/upload-sarif@v4` step (SHA-pinned) + `security-events: write` and `actions: read` permissions. Use `if: always()` per AC, `continue-on-error: true` to guard against missing GHAS, `category: megalinter` for differentiation. Place after artifact upload, before fail gate.
- SARIF file path: `megalinter-reports/megalinter-report.sarif` (MegaLinter default, already generated)
- Risk: private repos require GitHub Code Security/GHAS for Code Scanning — `continue-on-error: true` mitigates gracefully
- Challenge: skipped — trivial config change, no competing options
- Confidence: 0.90
- Commit: 662a9192
[[2026-05-08]]
## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | Single concern: add SARIF upload step to existing workflow |
| Interface clarity | PASS (after refine) | Original AC missing permissions, continue-on-error, category, exact path, placement. Refined to 6 verifiable lines. |
| Dependency correctness | PASS | No deps needed; parent #1413 is context-only |
| Module layering | N/A | Infrastructure/CI config |
| TDD compliance | PASS | No testable Python; tagged `type:config` for test-writer pass-through |
| KISS/YAGNI | PASS | One step + two permission lines, minimal |
| Premise challenge | PASS | GitHub Code Scanning via SARIF is standard; no existing alternative in repo |
| Pattern consistency | PASS | SHA pinning, `if: always()`, `continue-on-error: true` all follow existing workflow patterns |
| Security surface | PASS | `security-events: write` is narrowly scoped and required for the feature |
| Single domain | PASS | Infrastructure/CI only |

### AC Refinements Applied
- Added exact SARIF path (`megalinter-reports/megalinter-report.sarif`)
- Added `category: megalinter` requirement
- Added `continue-on-error: true` requirement
- Added permissions requirement (`security-events: write`, `actions: read`)
- Added placement constraint (after artifact upload, before fail gate)
- Added SHA pinning requirement

### Test Depth
- Max depth: 0
- Test-writer: SKIP (all td:0)

### Challenge Results
- Challenger: SKIPPED — all td:0
- N/A

### Verdict: APPROVE
### Action Taken: Refined AC from 3 vague lines to 6 precise verifiable lines. Added `type:config` tag for test-writer pass-through. Advanced to `todo`.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- All AC lines annotated (td:0); architect flagged "Test-writer: SKIP (all td:0)".
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: updated .github/workflows/megalinter.yml
- Changes applied:
  - Added job permissions: `actions: read` and `security-events: write`
  - Added `Upload SARIF to GitHub Code Scanning` step using `github/codeql-action/upload-sarif@68bde559dea0fdcac2102bfdf6230c5f70eb485e` (v4, SHA-pinned)
  - Step config: `if: always()`, `continue-on-error: true`, `sarif_file: megalinter-reports/megalinter-report.sarif`, `category: megalinter`
  - Placement: directly after `Upload MegaLinter reports` artifact step (and before terminal fail gate)
- Tests: N/A (td:0 config task; no TestFromAC classes or test paths)
- Coverage: N/A (config-only change)
- Lint: quality-runner invoked; Python ruff is not applicable to YAML workflow files (reported false positives due to file-type mismatch)
- Evidence summary:
  - YAML/workflow structure check: no errors reported for .github/workflows/megalinter.yml
  - Quality-runner report captured non-applicability for pytest/coverage and ruff-on-YAML mismatch
- Commit: 53fe72ac4e80fc1eb41b79f1fabf03c773db7776
[[2026-05-08]]
## Review Evidence
### Test Results
- N/A. All acceptance criteria are annotated `(td:0)` and the task is a YAML-only workflow change, so test-writer skip is correct.
- No prior `## Review Evidence` section exists in `.owlbear/kanban/tasks/1417-add-sarif-upload-to-github-code-scanning-in-megalinter-workflow.md`; this is the first review cycle.

### Lint Results
- `quality-runner` scoped lint-only dispatch could not run for this td:0 task because its input contract requires non-empty `test_paths` in `mode=scoped`.
- Fallback syntax validation succeeded: `get_errors` reported `No errors found` for `.github/workflows/megalinter.yml`.

### Coverage Data
- N/A for td:0 infrastructure/config work.

### Changed Scope
- Builder notes scope the implementation to `.github/workflows/megalinter.yml`.
- Builder commit is present in git logs: `53fe72ac4e80fc1eb41b79f1fabf03c773db7776` with message `ci: upload megalinter SARIF to code scanning (#1417, builder)`.

### Security Review
- Reviewed YAML block introduces no secrets, shell interpolation, path input handling, or deserialization risks.
- The new action is GitHub-owned and SHA-pinned.

### AC Compliance
| AC Line | Evidence | Status |
|---|---|---|
| P1: `github/codeql-action/upload-sarif` step added to `.github/workflows/megalinter.yml`, SHA-pinned per workflow convention | `.github/workflows/megalinter.yml:72-75` shows `Upload SARIF to GitHub Code Scanning` using `github/codeql-action/upload-sarif@68bde559dea0fdcac2102bfdf6230c5f70eb485e` | PASS |
| P1: Step uses `sarif_file: megalinter-reports/megalinter-report.sarif` and `category: megalinter` | `.github/workflows/megalinter.yml:77-78` | PASS |
| P2: Step uses `if: always()` condition | `.github/workflows/megalinter.yml:73` | PASS |
| P2: Step uses `continue-on-error: true` to handle missing GHAS gracefully | `.github/workflows/megalinter.yml:74` | PASS |
| P2: Job permissions include `security-events: write` and `actions: read` | `.github/workflows/megalinter.yml:42-46`, with `actions: read` at line 43 and `security-events: write` at line 46 | PASS |
| P2: Step placed after `Upload MegaLinter reports` artifact step, before `Fail if lint failed` gate | Artifact step begins at `.github/workflows/megalinter.yml:64`; SARIF step begins at line 72; fail gate begins at line 156 | PASS |

### Deductions
- `-0.03`: canonical `quality-runner` lint evidence was unavailable for this td:0 review because scoped mode rejects empty `test_paths`; used direct YAML diagnostics instead.
- `-0.02`: commit diff and dirty-tree contamination checks were not available through the current tool surface; scoped evidence relied on current artifact state, builder notes, and git-log commit presence.

### Verdict
- PASS -> docs
- Confidence: 0.93

### Action
- Advanced task to `docs`.
[[2026-05-08]]
## Docs Gate
### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | Grep of README.md, README-consumer.md, SECURITY.md, setup/*.md, share/README.md — no references to megalinter, SARIF, or code-scanning |
| 2 | Module docstrings | No | N/A | YAML-only workflow change; no Python modules created or modified |
| 3 | External attribution | Yes | Verified | `.owlbear/sources/overview.md` lines 5–12 already contain 4 source rows for task #1417 (populated by researcher) |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1417-sarif-upload-code-scanning.md` exists and is linked in task body |
| 5 | Diagram maintenance (describes match) | No | N/A | No diagram in share/diagrams/*.excalidraw describes `.github/workflows/megalinter.yml` |
| 6 | Explicit diagram creation | No | N/A | No explicit diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted; workflow file modified only |

### Scope Classification
| File | Scope | Action |
|------|-------|--------|
| `.github/workflows/megalinter.yml` | OUT | N/A — CI config, not an IN-scope doc |

### Files Updated
- None

### Child Tasks Created
- None

### Scratch Files Cleaned
- None (no `.owlbear/scratch/1417-*` files found)
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| P1: `github/codeql-action/upload-sarif` step added, SHA-pinned | `.github/workflows/megalinter.yml:72-75` — `github/codeql-action/upload-sarif@68bde559dea0fdcac2102bfdf6230c5f70eb485e` | PASS |
| P1: Step uses `sarif_file: megalinter-reports/megalinter-report.sarif` and `category: megalinter` | `.github/workflows/megalinter.yml:77-78` | PASS |
| P2: Step uses `if: always()` condition | `.github/workflows/megalinter.yml:73` | PASS |
| P2: Step uses `continue-on-error: true` | `.github/workflows/megalinter.yml:74` | PASS |
| P2: Job permissions include `security-events: write` and `actions: read` | `.github/workflows/megalinter.yml:43` (`actions: read`) and `:46` (`security-events: write`) | PASS |
| P2: Step placed after artifact upload, before fail gate | Artifact upload at L64-70, SARIF upload at L72-78, fail gate at L156 | PASS |

### Test Results
- pytest: 2794 passed, 356 failed, 4 skipped — all failures are pre-existing cockpit/Pydantic debt, none in task scope (YAML-only change)
- ruff: 12 violations — all in Python files (`serve/knowledge/`, `serve/tools/`), none task-related

### Architect Quality: 5/5
AC refined from 3 vague lines to 6 precise verifiable lines during arch review. Each line is specific, measurable, and maps to a single assertion. No builder improvisation needed.

### Deduction Breakdown
- No AC lines without evidence: 0 deductions
- Lint violations in task scope: none → 0 deductions
- AC quality 5/5: 0 deductions
- Reviewer evidence section: present, detailed, PASS → 0 deductions
- Full-suite failures in task scope: none → 0 deductions

### Confidence: .98
(-.02 for pre-existing suite failures — not caused by this task, but noted for awareness)

### Action: archive