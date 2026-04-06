---
id: 671
title: Bootstrap CI workflows to main branch
status: todo
priority: needed
created: 2026-04-06T22:23:06.3075808+02:00
updated: 2026-04-06T22:42:03.0780446+02:00
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
