---
id: 612
title: Write consumer-focused README for main branch
status: backlog
priority: needed
created: 2026-04-04T21:55:11.0661506+02:00
updated: 2026-04-04T21:55:11.0661506+02:00
tags:
    - scope:infra
    - type:docs
    - phase-2
parent: 610
class: standard
---

## Summary

Write a consumer-focused README (README-consumer.md) on the dev branch. The sync workflow renames it to README.md on main. The existing README.md on dev remains the dev project README.

## Acceptance Criteria

- [ ] AC1: README-consumer.md exists on dev branch
- [ ] AC2: Contains: overview, prerequisites, quick start (clone + setup/init.py), directory layout (share/serve/seed/setup only), verification steps
- [ ] AC3: Does NOT reference dev-only content (tests, kanban, research, orchestrator CLI, knowledge loader)
- [ ] AC4: Mentions how to get updates (git pull)
- [ ] AC5: Links to setup/setup-guide.md and setup/sharing-guide.md
- [ ] AC6: Sync workflow configured to rename README-consumer.md to README.md on main

## Notes

Dev README.md stays as-is (describes the full dev workspace, orchestrator, knowledge, etc.).
