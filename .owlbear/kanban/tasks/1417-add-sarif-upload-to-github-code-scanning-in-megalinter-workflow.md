---
id: 1417
title: Add SARIF upload to GitHub Code Scanning in MegaLinter workflow
status: review
priority: nice-to-have
created: 2026-05-07T23:28:57.957311+00:00
updated: 2026-05-08T14:17:24.445914+00:00
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