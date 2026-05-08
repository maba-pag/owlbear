---
id: 1416
title: Add push/PR triggers to MegaLinter workflow
status: review
priority: needed
created: 2026-05-07T23:28:55.138508+00:00
updated: 2026-05-08T01:01:57.283081+00:00
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