---
id: 613
title: Create GitHub Actions sync workflow (dev to main)
status: review
priority: nice-to-have
created: 2026-04-04T21:55:26.1899523+02:00
updated: 2026-04-06T04:03:27.3219842+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
    - type:config
parent: 610
depends_on:
    - 611
    - 612
class: standard
---

## Summary

Create a GitHub Actions workflow (.github/workflows/sync-to-main.yml) on the dev branch that copies product files from dev to main on manual dispatch (workflow_dispatch).

## Workflow Logic

1. Trigger: workflow_dispatch (manual run from GitHub UI or gh CLI)
2. Checkout dev branch
3. Create a clean temporary directory
4. Validate all include-list paths exist on dev (exit non-zero if any missing)
5. Copy ONLY these files/dirs into temp:
   - Directories: share/, serve/, seed/, setup/
   - Files: pyproject.toml, uv.lock, .python-version, .gitignore, SECURITY.md
   - README-consumer.md (placed as README.md in temp)
6. Create orphan commit from temp contents (no dev branch history)
7. Force-push orphan commit to main branch
8. Commit message: "sync: update from dev (workflow dispatch)"

## Acceptance Criteria

- [ ] AC1: .github/workflows/sync-to-main.yml exists on dev branch
- [ ] AC2: Workflow trigger is workflow_dispatch only (no push, schedule, or PR triggers)
- [ ] AC3: Workflow syncs ONLY these paths from dev to main: directories share/, serve/, seed/, setup/; files pyproject.toml, uv.lock, .python-version, .gitignore, SECURITY.md, and README-consumer.md (placed as README.md on main). No other files.
- [ ] AC4: Workflow validates all AC3 include-list paths exist on dev before committing. Exits with non-zero status if any are missing.
- [ ] AC5: Workflow creates an orphan commit on main (no dev branch history) and force-pushes. Commit message: "sync: update from dev (workflow dispatch)"
- [ ] AC6: .gitignore from dev is copied as-is (extra exclusions for dev-only dirs are inert on main)
- [ ] AC7: Workflow uses GITHUB_TOKEN with contents:write permission. Assumes no branch protection rules on main. If branch protection is added later, file follow-up task for auth changes.

## Notes

- pyproject.toml skills-ref is already in optional validation group (#614 archived). Workflow copies pyproject.toml as-is; uv sync on main will not install it.
- Consumer .gitignore: dev .gitignore is copied as-is. Extra exclusion lines for .owlbear/, store/, tests/, etc. are harmless on main since those dirs dont exist there.
- Dry-run mode (workflow input to preview without pushing) is a future enhancement, not in-scope.
- If branch protection is later enabled on main (require reviews, require checks, deny force-push), the workflow must use a PAT or deploy key with bypass permissions. File as separate follow-up task.
- #615 (First sync: validate clean main branch) is the end-to-end validation task. The sync workflow (#613) produces the mechanism; #615 validates the output.

## Architecture Review

### Evaluation

| Criterion | Assessment | Notes |
|-----------|-----------|-------|
| Single responsibility | PASS | One deliverable: sync workflow YAML file |
| Interface clarity | PASS (refined) | Original 9 ACs reduced to 7 precise, verifiable lines. Removed duplicative/stale/optional ACs. |
| Dependency correctness | PASS | #611 (dev branch, in-progress) and #612 (consumer README, archived). Both correct. |
| Module layering | N/A | Infrastructure task, no Python modules |
| TDD compliance | PASS | Added type:config pass-through tag for test-writer |
| KISS/YAGNI | PASS (refined) | Removed dry-run (optional/future), removed consumer validation (belongs to #615) |
| Premise challenge | PASS | Orphan+force-push is correct strategy for auto-generated consumer branch. Alternatives evaluated: git subtree split (overkill), manual copy (history pollution), API tree upload (over-complex). |
| Pattern consistency | N/A | First workflow in repo, no existing patterns to follow |
| Security surface | PASS | Include-list approach prevents dev file leaks. GITHUB_TOKEN scoped to repo. Manual trigger only. No secrets embedded. |
| Single domain | PASS | scope:infra only |

### Refinements Applied

1. Removed AC4 ("no dev-only files leak... etc.") -- vague exclusion list with "etc." Redundant with include-list approach (AC3).
2. Removed AC6 ("pyproject.toml skills-ref handled") -- stale. #614 already moved skills-ref to optional validation group. pyproject.toml copied as-is.
3. Removed AC7 ("dry-run mode, optional") -- optional ACs create builder/reviewer ambiguity. Moved to Notes as future enhancement.
4. Removed AC8 ("workflow completes successfully") -- duplicates #615 AC1 (end-to-end validation).
5. Removed AC9 ("consumer can clone and use") -- duplicates #615 AC4-AC6 (consumer validation scope).
6. Added AC4 (validation checkpoint): workflow exits non-zero if include-list paths missing on dev. Prevents silent partial syncs.
7. Rewrote AC7: explicit GITHUB_TOKEN usage with documented branch-protection assumption.
8. Rewrote AC3: self-contained include list (was "see include list above").
9. Clarified .gitignore approach in AC6 and Notes (copy as-is, KISS).
10. Added type:config pass-through tag (type:build not in non-impl pass-through list, per #611 precedent).

### Challenge Results

- Challenger: RECONSIDER (confidence: 0.75)
- Concerns: (1) AC7 contradicted original Notes on branch protection -- resolved by documenting assumption and follow-up path. (2) Missing validation checkpoint for include-list paths -- added as AC4. (3) AC3 phrasing ambiguity -- rewrote as self-contained list.
- Architect response: accepted all three. Integrated into refinements 6, 7, and 8.

### Verdict: APPROVE (after refinement)
### Action Taken: Rewrote 9 ACs into 7 precise, verifiable lines. Removed stale/duplicative/optional ACs. Added validation checkpoint (AC4), type:config tag. Documented branch-protection assumption. Advanced to todo.

[[2026-04-05]] Sun 20:29
Refined 9 ACs into 7 precise, verifiable lines. Removed stale AC6 (#614 resolved), duplicative AC8/AC9 (#615 scope), optional AC7 (dry-run future enhancement), vague AC4 ("etc."). Added validation checkpoint (AC4), self-contained include-list (AC3), explicit GITHUB_TOKEN assumption (AC7). type:config pass-through tag added. Challenger RECONSIDER (0.75) on branch-protection and validation checkpoint -- both integrated.

[[2026-04-05]] Sun 21:56
Non-implementation task (tagged type:config) — no tests applicable. Deliverable is .github/workflows/sync-to-main.yml (YAML file). No testable Python interfaces exist. All 7 ACs describe YAML workflow structure, shell script behavior, and GitHub Actions semantics — not Python code. Passing through to builder.

[[2026-04-06]] Mon 04:03
## Builder Notes\n\n### Files Changed\n- `.github/workflows/sync-to-main.yml` (created)\n\n### AC Verification\n- AC1: File exists at `.github/workflows/sync-to-main.yml` ✓\n- AC2: `on: workflow_dispatch:` only — no push/schedule/PR triggers ✓\n- AC3: Include-list: share/, serve/, seed/, setup/, pyproject.toml, uv.lock, .python-version, .gitignore, SECURITY.md, README-consumer.md→README.md. No other paths. ✓\n- AC4: Validate step iterates all include-list paths, sets `failed=1` for any missing, exits 1 if `$failed -ne 0` ✓\n- AC5: `git init` in temp dir → orphan commit → `git push origin HEAD:main --force` with message \"sync: update from dev (workflow dispatch)\" ✓\n- AC6: `.gitignore` copied as-is via `cp .gitignore \"$TREE/\"` ✓\n- AC7: `permissions: contents: write` declared; GITHUB_TOKEN used in remote URL for push ✓\n\n### Notes\n- No Python code changed; YAML-only deliverable. Lint not applicable.\n- Auth via `x-access-token:${{ secrets.GITHUB_TOKEN }}` embedded in remote URL — standard GitHub Actions pattern for force-push.\n- Unblocks #615.
