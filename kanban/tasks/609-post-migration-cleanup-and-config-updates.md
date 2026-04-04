---
id: 609
title: Post-migration cleanup and config updates
status: backlog
priority: needed
created: 2026-04-04T20:32:03.4328653+02:00
updated: 2026-04-04T20:32:03.4328653+02:00
tags:
    - scope:infra
    - type:build
    - phase-2
depends_on:
    - 604
    - 605
    - 606
    - 607
    - 608
parent: 598
class: standard
---

## Summary

Update .vscode/settings.json (files.exclude, search.exclude), .gitignore, .pre-commit-config.yaml, and any other config files for the new folder structure. Delete empty docs/ folder. Update README with new directory layout.

## Acceptance Criteria

- [ ] AC1: .vscode/settings.json files.exclude updated (remove docs/scratch, add .owlbear/scratch)
- [ ] AC2: .vscode/settings.json search.exclude updated for new paths
- [ ] AC3: .owlbear/ visible in VS Code file explorer (not in files.exclude)
- [ ] AC4: .gitignore updated for store/, .owlbear/scratch/, etc.
- [ ] AC5: .pre-commit-config.yaml hook paths updated if applicable
- [ ] AC6: docs/ directory deleted (empty after migration)
- [ ] AC7: README.md directory layout table reflects five-tier model
- [ ] AC8: Decision doc moved from docs/decisions/pending/ to .owlbear/decisions/resolved/ and marked Resolved
- [ ] AC9: owlbear-project.json schema_version bumped if needed
- [ ] AC10: Empty dirs have .gitkeep where needed

## Notes

This is the cleanup and finalization task. After this, the migration is complete.
