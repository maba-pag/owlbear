---
id: 669
title: Remove dead Docker ecosystem from dependabot
status: todo
priority: needed
created: 2026-04-06T22:22:41.1186478+02:00
updated: 2026-04-06T22:42:02.9240532+02:00
tags:
    - scope:ci
    - type:fix
parent: 672
class: standard
---

## Objective\nRemove the dead Docker ecosystem from dependabot config.\n\n## Context\nThe `docker` ecosystem was added to track MegaLinter image updates. However, MegaLinter is used as a GitHub Action (`uses: oxsecurity/megalinter/...@SHA`), which is tracked by the `github-actions` ecosystem. The `docker` ecosystem looks for Dockerfile/docker-compose files. The project has no Docker files (only third-party files inside v1/.venv/). This ecosystem block does nothing.\n\n## Acceptance Criteria\n- [ ] Docker ecosystem block removed from .github/dependabot.yml\n- [ ] github-actions ecosystem still covers MegaLinter action updates\n- [ ] pip ecosystem unchanged\n\n## Files Affected\n- .github/dependabot.yml
