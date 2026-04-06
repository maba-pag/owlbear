---
id: 668
title: Fix megalinter for private repo constraints
status: todo
priority: needed
created: 2026-04-06T22:22:31.9554503+02:00
updated: 2026-04-06T22:42:02.8451662+02:00
tags:
    - scope:ci
    - type:fix
parent: 672
class: standard
---

## Objective\nFix megalinter.yml for private repo constraints: SARIF upload requires GHAS (not available), APPLY_FIXES has no write permissions to commit.\n\n## Context\nmaba-pag/owlbear is a private repo. `github/codeql-action/upload-sarif` requires GitHub Advanced Security or a public repo. The SARIF step will error. Additionally, `.mega-linter.yml` configures `APPLY_FIXES` for ruff-format + markdownlint, but the job only has `contents: read` permissions, so fixes are silently lost.\n\n## Acceptance Criteria\n- [ ] SARIF upload step removed (private repo without GHAS)\n- [ ] APPLY_FIXES removed from .mega-linter.yml (no write permissions to commit fixes)\n- [ ] Upload-artifact step for reports preserved (primary output mechanism)\n- [ ] Job summary step still reports pass/fail\n- [ ] `security-events: write` permission removed (no longer needed without SARIF)\n\n## Files Affected\n- .github/workflows/megalinter.yml\n- .mega-linter.yml
