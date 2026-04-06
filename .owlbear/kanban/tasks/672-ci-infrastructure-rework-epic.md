---
id: 672
title: CI infrastructure rework (epic)
status: todo
priority: needed
created: 2026-04-06T22:41:55.5351404+02:00
updated: 2026-04-06T22:41:55.5351404+02:00
tags:
    - scope:ci
    - type:epic
class: standard
---

## Objective\nEpic for CI infrastructure rework: fix all workflow issues, switch sync strategy, bootstrap to main.\n\n## Subtasks\n- #667 Rewrite sync-to-main with incremental commit strategy\n- #668 Fix megalinter for private repo constraints\n- #669 Remove dead Docker ecosystem from dependabot\n- #670 Create .cspell.json for project vocabulary\n- #671 Bootstrap CI workflows to main branch\n\n## Context\nAudit found 11 issues across sync-to-main.yml, megalinter.yml, .mega-linter.yml, dependabot.yml. Key findings: force-push destroys main history, include-list missing .github/, SARIF upload fails on private repo, APPLY_FIXES silently lost, docker ecosystem is dead, dependabot not running (config only on dev).
