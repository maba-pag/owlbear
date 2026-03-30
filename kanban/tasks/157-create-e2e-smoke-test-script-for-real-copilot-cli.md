---
id: 157
title: Create E2E smoke test script for real Copilot CLI
status: ideation
priority: important
created: 2026-03-29T19:34:05.2150485+02:00
updated: 2026-03-29T19:34:05.2150485+02:00
tags:
    - phase-2
    - scope:orchestrator
    - type:test
depends_on:
    - 20
    - 22
class: standard
---

## Objective
Manual smoke test script that validates the full stack with real Copilot CLI.

## Acceptance Criteria
- [ ] Script at scripts/e2e_smoke.py
- [ ] Creates temp task on kanban board
- [ ] Runs owlbear dispatch targeting temp task
- [ ] Waits for completion with configurable timeout (default 5 min)
- [ ] Checks board state and prints PASS/FAIL
- [ ] Cleans up temp task on exit
- [ ] Documents prerequisites (Copilot CLI installed, authenticated)
- [ ] Script header documents manual steps required

## Context
See docs/research/e2e-dispatch-test.md S3.3 (Layer 2). Supplements the automated integration test.
