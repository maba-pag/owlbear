---
id: 1416
title: Add push/PR triggers to MegaLinter workflow
status: archived
priority: medium
created: 2026-05-07T23:28:55.138508+00:00
updated: 2026-05-08T01:34:17.620252+00:00
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

Add automatic triggers to `.github/workflows/megalinter.yml` — currently manual-dispatch only. At minimum `push: branches: [dev]`. Consider `pull_request` trigger. See `.owlbear/research/1413-ci-sast-baseline.md` gap G1.

## Acceptance Criteria
P1: MegaLinter workflow triggers on push to dev branch (td:0)
P1: MegaLinter workflow triggers on pull_request to dev branch (td:0)
P2: Manual dispatch trigger (workflow_dispatch) preserved unchanged (td:0)
P2: Workflow file committed with new triggers (td:0)

## Research

**Finding:** Trivial YAML trigger addition. Official MegaLinter template confirms the pattern. No blockers, no alternative approaches needed.

**Implementation spec:**
Add `push: branches: [dev]` and `pull_request: branches: [dev]` to the existing `on:` block in `.github/workflows/megalinter.yml`. Keep `workflow_dispatch` as-is. No other changes needed — concurrency group, VALIDATE_ALL_CODEBASE, and permissions are already correct.

**Tier:** T1 (config change) — no DR required.
**Confidence:** 0.95 — standard GitHub Actions pattern, matches official template.

## Architecture Review
### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One config change to one file |
| Interface clarity | PASS | Triggers and branches clearly specified |
| Dependency correctness | PASS | No deps needed |
| Module layering | N/A | CI config, not source code |
| TDD compliance | PASS | Config-only, tagged type:config |
| KISS/YAGNI | PASS | Minimal trigger addition |
| Premise challenge | PASS | Workflow IS manual-only; auto triggers needed for CI value |
| Pattern consistency | PASS | Standard GHA on-push/PR pattern |
| Security surface | PASS | pull_request (not _target) = fork PRs read-only, no secrets; autofix steps gated by inputs.fix which is falsy on non-dispatch events |
| Single domain | PASS | scope:infra only |

### Challenge Results
- Challenger: SKIPPED — all td:0
- Architect response: N/A

### Test Depth
- Max depth: 0
- Test-writer: SKIP

### Verdict: APPROVE
### Action Taken: Refined AC to explicitly include PR trigger per research findings. Added type:config tag for test-writer pass-through. Advanced to todo.
[[2026-05-08]]
Architecture review complete. T1 config-only task — trivial YAML trigger addition to existing MegaLinter workflow. Security surface verified: pull_request (not _target) is safe for forks; autofix steps gated by inputs.fix. All AC lines td:0; tagged type:config for test-writer pass-through.
[[2026-05-08]]
## Test-Writer Notes
- Non-implementation task (tagged type:config) — no tests applicable.
- All AC lines are td:0 (config-only YAML trigger addition to .github/workflows/megalinter.yml).
- Passing through to builder.
[[2026-05-08]]
## Builder Notes
- Implementation: updated .github/workflows/megalinter.yml to add `push` and `pull_request` triggers scoped to `dev` under the existing `on` block.
- Scope: single-file, surgical YAML change; `workflow_dispatch` block preserved unchanged.
- Tests: N/A (td:0 config-only workflow task; no executable test targets).
- Coverage: N/A (no Python/TS source changes).
- Lint: N/A for this task scope; quality-runner reported no applicable lint/test targets.
- Evidence summary: workflow trigger AC now satisfied (`push` + `pull_request` on `dev` present), and committed as `60f88439` with only `.github/workflows/megalinter.yml` staged.
[[2026-05-08]]
## Review Evidence
### Test Results
- quality-runner: no applicable executable test targets for this td:0 config-only workflow change.

### Lint: N/A via quality-runner; static diagnostics clean
- quality-runner: no applicable local lint target in the standard Python/TS toolchain for .github/workflows/megalinter.yml.
- IDE diagnostics: no YAML errors in .github/workflows/megalinter.yml.
- Repo lint coverage: .mega-linter.yml:22,75-76 includes ACTION_ACTIONLINT and scopes it to .github/workflows/*.yml, so this file will be validated in CI.

### Coverage: N/A
- Config-only YAML change; no code coverage target.

### Pass 1 — CRITICAL
#### Test-Writer AC Coverage
| AC Line | Mapped Test | Would Fail If AC Violated? | Verdict |
|---------|-------------|---------------------------|---------|
| P1: MegaLinter workflow triggers on push to dev branch (td:0) | N/A | N/A | SKIP (td:0) |
| P1: MegaLinter workflow triggers on pull_request to dev branch (td:0) | N/A | N/A | SKIP (td:0) |
| P2: Manual dispatch trigger (workflow_dispatch) preserved unchanged (td:0) | N/A | N/A | SKIP (td:0) |
| P2: Workflow file committed with new triggers (td:0) | N/A | N/A | SKIP (td:0) |

#### Security Review
- No issues found.
- The workflow adds `pull_request`, not `pull_request_target` (.github/workflows/megalinter.yml:8).
- Auto-fix publication remains gated behind `inputs.fix` / `inputs.fix_mode` (.github/workflows/megalinter.yml:38,40,73,88,93,105-107).
- No hardcoded secrets introduced; top-level permissions remain declared and no new dependency/integration surface was added beyond the trigger expansion.

#### Test Integrity
| Original Test | Change Made | Assessment |
|---------------|-------------|------------|
| N/A | No TestFromAC_* tests exist for this td:0 task | SKIP |

#### Test Quality
| Dimension | Rating | Evidence |
|-----------|--------|----------|
| Assertion specificity | N/A | td:0 config task; no task tests |
| Negative/error-path coverage | N/A | td:0 config task; no task tests |
| Manual mutation reasoning | N/A | Artifact verification only |
| Test independence | N/A | td:0 config task; no task tests |
| Descriptive test names | N/A | td:0 config task; no task tests |

#### Data Safety
- No issues found. Change is limited to GitHub Actions trigger configuration.

#### Implementation-Aware Gaps
- No significant untested paths within task scope. The only changed contract is workflow trigger wiring, verified directly in the workflow YAML.

#### Builder Process Quality
| Metric | Value |
|-------|-------|
| Builder Notes sections | 1 |
| Approach variation | N/A |
| Assessment | CLEAN |

### Pass 2 — INFORMATIONAL
- Review used artifact-based commit evidence because this reviewer tool surface could not execute git diff/git status directly.
- Commit existence is independently evidenced by .git/logs/HEAD:2230 and .git/logs/refs/heads/dev:2055 for commit 60f884398bbb0601cb5781c593ba8a7ac1f846db.
- The task file records the builder's scoped change claim at .owlbear/kanban/tasks/1416-add-push-pr-triggers-to-megalinter-workflow.md:77; I could not independently inspect the full commit diff, so confidence is reduced slightly.
- No prior `## Review Evidence` header exists in the task file; this is the first review cycle.

### AC Compliance
| AC Line | Evidence | Mapped Test | Status |
|---------|----------|-------------|--------|
| P1: MegaLinter workflow triggers on push to dev branch (td:0) | .github/workflows/megalinter.yml:5-7 shows `push` with branch `dev` | N/A | PASS |
| P1: MegaLinter workflow triggers on pull_request to dev branch (td:0) | .github/workflows/megalinter.yml:8-10 shows `pull_request` with branch `dev` | N/A | PASS |
| P2: Manual dispatch trigger (workflow_dispatch) preserved unchanged (td:0) | .github/workflows/megalinter.yml:11-23 retains `workflow_dispatch` and its `fix` / `fix_mode` inputs; downstream gating remains at lines 38,40,73,88,93,105-107 | N/A | PASS |
| P2: Workflow file committed with new triggers (td:0) | .git/logs/HEAD:2230 and .git/logs/refs/heads/dev:2055 record builder commit `60f884398bbb0601cb5781c593ba8a7ac1f846db`; live workflow file contains the new triggers; task file line 77 records `.github/workflows/megalinter.yml` as the staged scope | N/A | PASS |

### Confidence: 0.93
### Verdict: PASS

### Post-task Reflection
- Git diff/status were not available from this reviewer tool surface; reflog plus live-file inspection was the workable fallback.
- td:0 workflow tasks need static artifact review rather than pytest/coverage gates.
- IDE diagnostics plus CI actionlint configuration provided useful secondary proof for YAML validity.
[[2026-05-08]]
## Docs Gate

### Checklist
| # | Check | Applies? | Status | Evidence |
|---|-------|----------|--------|----------|
| 1 | Descriptive prose docs | No | N/A | No IN-scope README or guide references MegaLinter push/PR triggers; grep across *.md returned only kanban task files and `.github/copilot-instructions.md` (both OUT of scope) |
| 2 | Module docstrings | No | N/A | No Python modules changed |
| 3 | External attribution | No | N/A | No external repo cloned; standard GHA trigger pattern, no attributable external source |
| 4 | Research doc | Yes | Verified | `.owlbear/research/1413-ci-sast-baseline.md` exists and is referenced in task body (gap G1) |
| 5 | Diagram maintenance (describes match) | No | N/A | doc-index has no describes entry matching `.github/workflows/megalinter.yml` |
| 6 | Explicit diagram creation | No | N/A | No diagram creation request in task body |
| 7 | Deletion detection | No | N/A | No files deleted |

### Scope Classification
- `.github/workflows/megalinter.yml` → **OUT of scope** (CI workflow config — not in IN-scope list)

### Result
No docs impact. Single changed file is OUT-of-scope CI config. All 7 items N/A.

### Files Updated
None.

### Scratch Files
No `.owlbear/scratch/1416-*` files found.
[[2026-05-08]]
## Audit
### AC Verification
| AC Line | Evidence | Status |
|---------|----------|--------|
| P1: MegaLinter workflow triggers on push to dev branch (td:0) | `.github/workflows/megalinter.yml:5-7` — `push: branches: [dev]` present | PASS |
| P1: MegaLinter workflow triggers on pull_request to dev branch (td:0) | `.github/workflows/megalinter.yml:8-10` — `pull_request: branches: [dev]` present | PASS |
| P2: Manual dispatch trigger (workflow_dispatch) preserved unchanged (td:0) | `.github/workflows/megalinter.yml:11-23` — `workflow_dispatch` with `fix` and `fix_mode` inputs intact | PASS |
| P2: Workflow file committed with new triggers (td:0) | `git log` confirms commit `60f88439` — `chore: add dev push/pr triggers to megalinter workflow (#1416, builder)` | PASS |

### Test Results
- pytest: 4836 passed, 215 failed, 4 skipped, 6 errors — **0 failures in task scope** (all pre-existing background)
- vitest: 1045 passed, 3 failed — **0 failures in task scope**
- ruff: 13 violations — **0 in task-changed files**
- eslint: 4 violations (1 fatal config) — **0 in task scope**

### Architect Quality: 5/5
Specific, complete AC for a config-only task. Security surface correctly addressed (pull_request vs pull_request_target). Test depth td:0 appropriate. No gaps.

### Deduction Breakdown
- AC lines without evidence: 0 (all 4 PASS) → -0.00
- Lint in task scope: 0 → -0.00
- AC quality ≤ 3: no → -0.00
- Missing reviewer evidence: no (detailed section present, PASS at 0.93) → -0.00
- Full-suite failures in task scope: 0 → -0.00

### Confidence: 0.98
### Action: archive