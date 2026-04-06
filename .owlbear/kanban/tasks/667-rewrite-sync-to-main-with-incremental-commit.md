---
id: 667
title: Rewrite sync-to-main with incremental commit strategy
status: todo
priority: needed
created: 2026-04-06T22:22:21.0482147+02:00
updated: 2026-04-06T22:42:02.7172613+02:00
tags:
    - scope:ci
    - type:build
parent: 672
class: standard
---

## Objective\nRewrite sync-to-main.yml from orphan/force-push strategy to incremental commits on main's history. Expand the include-list to cover CI config files. Restore all UX features that were stripped.\n\n## Context\nCurrent sync creates orphan commits via `git init` + `git push --force`, destroying main's history every sync. The include-list is missing .github/, .mega-linter.yml, .editorconfig, .markdownlint.json. UX features (dry-run, diff preview, rich commit msg, full summary) were stripped by a pipeline task.\n\n## Acceptance Criteria\n- [ ] Incremental commits: new sync commits are children of main's HEAD (no force-push, no orphan)\n- [ ] First-ever sync handled: works when main branch doesn't exist yet\n- [ ] Include-list expanded: .github/, .mega-linter.yml, .editorconfig, .markdownlint.json added\n- [ ] Validation step covers all include-list paths\n- [ ] Dry-run input: workflow_dispatch boolean, skips push, shows preview\n- [ ] Dev metadata captured: short SHA, UTC date, actor\n- [ ] Diff preview: stat-diff between consumer tree vs current main\n- [ ] Rich commit message: `sync: dev@{sha} ({date}, {actor})`\n- [ ] Job summary: full details on success (diff, SHA, date, actor)\n- [ ] Failure summary: uses `if: always()` to report even on push failure\n- [ ] `fetch-depth: 0` justified (needed for incremental approach)\n- [ ] SHA-pinned actions (checkout v6.0.2)\n- [ ] Concurrency guard preserved\n\n## Design Notes\nIncremental approach:\n1. Checkout dev with full history\n2. Fetch origin/main (handle missing branch)\n3. Create branch from origin/main (or orphan if first sync)\n4. `git rm -rf .` to clear working tree\n5. `git checkout dev -- <include-list paths>`\n6. Handle README-consumer.md to README.md rename\n7. Commit as normal child of main\n8. Regular `git push` (no --force)\n\n## Files Affected\n- .github/workflows/sync-to-main.yml
