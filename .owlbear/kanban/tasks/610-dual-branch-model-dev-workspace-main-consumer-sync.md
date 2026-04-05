---
id: 610
title: 'Dual-branch model: dev (workspace) + main (consumer sync)'
status: backlog
priority: nice-to-have
created: 2026-04-04T21:54:46.295562+02:00
updated: 2026-04-05T00:35:53.0199344+02:00
tags:
    - scope:infra
    - type:restructure
    - phase-2
depends_on:
    - 598
    - 615
class: standard
---

## Summary

Set up the dual-branch model for owlbear: dev (full workspace, daily driver) and main (clean consumer-facing, auto-synced product subset).

## Context

OwlBear serves two roles: service provider for target projects and self-improving dev project. The dev branch holds everything (research, kanban, tests, v1 archive). The main branch holds only the product subset that consumers need.

A GitHub Actions workflow syncs product files from dev to main on manual dispatch. Consumers clone main; contributors work on dev.

## Architecture

```
dev (default working branch):
  share/ serve/ seed/ setup/          <- product files
  .owlbear/ store/ tests/ v1/ ...    <- dev-only files

main (consumer branch, auto-generated):
  share/ serve/ seed/ setup/          <- synced from dev
  pyproject.toml uv.lock README.md    <- synced from dev
  .python-version .gitignore SECURITY.md
```

## Acceptance Criteria

- [ ] AC1: dev branch created from current main
- [ ] AC2: dev set as default working branch (but main remains GitHub default for consumers)
- [ ] AC3: All subtasks (#611 through #615) completed
- [ ] AC4: Sync workflow tested end-to-end
- [ ] AC5: Consumer clone (main) works with setup/init.py

## Subtasks

#611 Create dev branch and push to remote
#612 Write consumer-focused README for main branch
#613 Create GitHub Actions sync workflow (dev to main)
#614 Move skills-ref to optional dependency group
#615 First sync: validate clean main branch

## Dependencies

Depends on #598 (five-tier folder restructure) and #615 (first sync validation).

## Risks

- GitHub default branch must be main (consumer-facing), but dev is the working branch
- pyproject.toml skills-ref dep must be handled for main (uv sync must not fail)
- First sync creates a diverged main that cannot be merged back to dev (by design)
