---
id: 613
title: Create GitHub Actions sync workflow (dev to main)
status: backlog
priority: nice-to-have
created: 2026-04-04T21:55:26.1899523+02:00
updated: 2026-04-05T00:35:43.7550941+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
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
4. Copy ONLY these files/dirs into temp:
   - share/
   - serve/
   - seed/
   - setup/
   - pyproject.toml (with skills-ref dependency removed or moved to optional group)
   - uv.lock
   - .python-version
   - .gitignore (consumer version, may need adjustment)
   - README-consumer.md (renamed to README.md)
   - SECURITY.md
5. Force-push temp contents to main branch (orphan commit or amend)
6. Commit message: "sync: update from dev (workflow dispatch)"

## Acceptance Criteria

- [ ] AC1: .github/workflows/sync-to-main.yml exists on dev branch
- [ ] AC2: Workflow trigger is workflow_dispatch only
- [ ] AC3: Only approved product files are synced (see include list above)
- [ ] AC4: No dev-only files leak to main (.owlbear/, store/, tests/, v1/, etc.)
- [ ] AC5: README-consumer.md renamed to README.md on main
- [ ] AC6: pyproject.toml skills-ref dependency handled (removed or made optional)
- [ ] AC7: Dry-run mode available (optional: workflow input to preview without pushing)
- [ ] AC8: Workflow completes successfully on manual dispatch
- [ ] AC9: Consumer can clone main, run uv sync, and use owlbear

## Notes

The workflow needs write access to the main branch. If branch protection is enabled, use a deploy key or PAT with bypass.

Consumer .gitignore may differ from dev .gitignore (e.g., no .owlbear/ exclusions needed on main since that dir doesnt exist there).
