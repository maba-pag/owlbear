---
id: 671
title: Bootstrap CI workflows to main branch
status: archived
priority: medium
created: 2026-04-06T22:23:06.3075808+02:00
updated: 2026-04-07T16:04:35.0147617+02:00
started: 2026-04-07T16:04:35.0147617+02:00
completed: 2026-04-07T16:04:35.0147617+02:00
tags:
    - scope:ci
    - type:user-action
parent: 672
depends_on:
    - 667
    - 668
    - 669
class: standard
---

## Objective\nBootstrap CI workflows to main branch so they're discoverable in GitHub Actions UI for manual dispatch.\n\n## Context\nGitHub Actions UI only shows `workflow_dispatch` workflows from the default branch (main). Currently no workflow files exist on origin/main. `gh workflow run --ref dev` may work via CLI even without the file on main (GitHub indexes from push events), but UI dispatch is impossible.\n\nThis task should be executed AFTER all other CI tasks (#667, #668, #669, #670) are committed to dev.\n\nDependabot also reads `.github/dependabot.yml` from the default branch only, so it's currently not running.\n\n## Acceptance Criteria\n- [ ] All CI changes committed to dev first (#667, #668, #669 at minimum)\n- [ ] sync-to-main dispatched once via `gh workflow run` or GitHub API targeting dev\n- [ ] After sync: .github/workflows/ visible on origin/main\n- [ ] After sync: .github/dependabot.yml visible on origin/main\n- [ ] After sync: megalinter.yml dispatchable from GitHub Actions UI\n- [ ] After sync: sync-to-main.yml dispatchable from GitHub Actions UI\n- [ ] tags: type:user-action (manual one-time operation)\n\n## Bootstrap Commands\n```bash\n# Option A: gh CLI\ngh workflow run sync-to-main.yml --ref dev\n\n# Option B: GitHub API\ncurl -X POST -H \"Authorization: bearer $GITHUB_TOKEN\" \\\n  https://api.github.com/repos/maba-pag/owlbear/actions/workflows/sync-to-main.yml/dispatches \\\n  -d '{\"ref\": \"dev\"}'\n```\n\n## Files Affected\nNone (operational task, no file changes)

[[2026-04-07]] Tue 11:37
## Architecture Review

### Evaluation
| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One concern: bootstrap CI workflows to main via sync dispatch |
| Interface clarity | PASS | AC specifies exact commands (`gh workflow run`), verification targets (UI dispatchability), and file visibility checks |
| Dependency correctness | PASS | #667 (done), #668 (done), #669 (done) — all satisfied. #670 correctly excluded (nice-to-have, independent) |
| Module layering | N/A | Operational task, no code modules |
| TDD compliance | N/A | type:user-action, no testable Python code |
| KISS/YAGNI | PASS | Minimal scope — one CLI command, then human verification |
| Premise challenge | PASS | GitHub Actions UI only shows workflow_dispatch workflows from default branch — confirmed by GitHub docs. Bootstrap is genuinely required. |
| Pattern consistency | PASS | Standard `gh workflow run` / GitHub API dispatch patterns |
| Security surface | PASS | Uses existing GITHUB_TOKEN via `gh` CLI auth, no new credentials or permissions |
| Single domain | PASS | CI domain only (scope:ci) |

### User-Action Detection (Criterion 13)
- Counter-signals: None (no function signatures, no test outcomes, not type:test/type:config)
- M1: AC defines no testable Python interface — YES (CLI commands + UI verification)
- M2: Completion can only be verified by human — YES (GitHub Actions UI dispatchability)
- S1: Physical-action verbs — YES ("dispatched")
- S2: External systems — YES (GitHub Actions UI, GitHub API)
- S3: Manual steps — YES (run workflow dispatch, verify UI visibility)
- Result: type:user-action CONFIRMED

### AC Quality
All 7 AC lines are precise and human-verifiable. Bootstrap commands provided in the body are correct. No refinement needed.

### Dependency Analysis
- #667 sync-to-main rewrite: done (the workflow being dispatched)
- #668 megalinter fix: done (will be synced to main)
- #669 dependabot cleanup: done (dependabot.yml will be synced)
- #670 .cspell.json: in review (not a dependency — correctly excluded; can bootstrap without it)

### Timing Note
Recommend waiting for #670 to reach done before dispatching, to avoid a second sync cycle. However, AC correctly marks this as optional ("at minimum").

### Challenge Results
- Challenger: SKIPPED (BLOCK verdict — challenger mandatory only for APPROVE)

### Scribe AR
- Scribe: FALLBACK — scribe agent not available in current session. Task body contains clear bootstrap commands and AC that serve as the action request.

### Verdict: BLOCK
### Action Taken: Blocked for user action. All dependencies satisfied. User should: (1) ensure all CI commits are pushed to origin/dev, (2) run `gh workflow run sync-to-main.yml --ref dev`, (3) verify workflows visible on origin/main and dispatchable from GitHub Actions UI.
